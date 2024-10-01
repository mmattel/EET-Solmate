import os
import sys
import json
import time
import schedule
from datetime import datetime
import solmate_connect as sol_connect
import solmate_env as sol_env
import solmate_utils as sol_utils

version = '7.2.1'

def query_once_a_day(smws_conn, route, data, mqtt_conn, print_response, endpoint):
	# send request but only when triggered by the scheduler
	# use only for requests with routes that change rarely, more requests can be added
	sol_utils.logging('Main: Once a day queries called by scheduler.')
	response = smws_conn.query_solmate(route, data)
	if response != False:
		if not 'timestamp' in response:
			# fake a timestamp into the response if not present
			response['timestamp'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
		if not 'operating_state' in response:
			# fake an operating_state into the response if not present, the content will be added in mqtt.
			response['operating_state'] = ''
		if print_response:
			sol_utils.print_request_response(route, response)
		if mqtt_conn:
			mqtt_conn.send_sensor_update_message(response, endpoint)

def main(self = None):
	# the main routine that covers all. must be called by a higher layer doing final error catching
	# the parameter self is optional. if not set, we have a default setup like with systemd
	# if set, it comes from appdaemon and holds the class access

	# version is defined on the module level
	global version

	try:
		# basic initialisation
		# get envvars to configure access either from file or from os/docker envvars
		sol_env.process_env(version, self)

		print_response = sol_utils.merged_config['general_print_response']

		# the paho-mqtt library check has been moved into solmate_mqtt.py

		# first validity config check for the solmates websocket address
		if 'eet_server_uri' not in sol_utils.merged_config.keys():
			# if the uri key is not present, exit.
			# if the uri key is present but empty or wrong, the error will be catched in the connection
			sol_utils.logging('Main: \'eet_server_uri\' was not defined in the configuration, exiting.')
			sys.exit()

		smws_conn = None
		mqtt_conn = None
		eet_connected = False
		mqtt_connected = False
		job_scheduler = False
		# necessary for very early failures during connecting which is before the while loop
		reboot_triggered = False

	except Exception as err:
		# if the error happened before successfully getting the envvars in process_env
		# construct the two mandatory envvars for logging, if not present
		sol_utils.merged_config.setdefault('general_console_print', True)
		sol_utils.merged_config.setdefault('general_console_timestamp', False)

		# log the error that was uncoverable, re-raise the error to document its trace
		sol_utils.logging(str(err))
		raise

	while True:
		# because things can always happen, we check connectivity and establish if not connected

		try:
			# in case no connection could be established,
			# the timer value in the error raised defines which timer to use
			if not eet_connected:
				# connect and authenticate, don't continue if this fails
				smws_conn, online, local = sol_connect.connect_solmate()

				# some api's are only available depending on local or cloud connection
				api_available = sol_connect.check_routes(smws_conn, local)
				eet_connected = True

			if not mqtt_connected:
				# connect and authenticate to mqtt if defined
				# mqtt_conn can either be false (mqtt not used) or contains the mqtt connection object
				mqtt_conn = sol_connect.connect_mqtt(api_available)
				# connected says, that technically the initialisation was successful
				mqtt_connected = True

			# get values from the 'get_solmate_info' route
			# start a scheduler for once-a-day requests
			# this content changes rarely, most likely the version number from time to time.
			# the scheduler gets deleted if there is any connection issue and resetup.
			schedule.every().day.at('23:45').do(
					query_once_a_day,
					smws_conn=smws_conn,
					route='get_solmate_info',
					data={},
					mqtt_conn=mqtt_conn,
					print_response=print_response,
					endpoint='info'
				)

			# run all already defined tasks in the scheduler to get a first response
			# only necessary to run once even if one of the connections are resetup
			if not job_scheduler:
				schedule.run_all()
				job_scheduler = True

			reboot_triggered = False

			while True:
			# loop to continuosly request live values or process commands from mqtt
				route = None
				value = None

				if mqtt_conn:
					# only if mqtt is active
					# process all write requests from the queue initiated by mqtt
					while sol_utils.mqtt_queue.qsize() != 0:
						# we have a message from mqtt because a value change or a button being pressed
						# data can be a multi entry in the dictionary like boost,
						# but for e.g. shutdown it is only one
						route, data = sol_utils.mqtt_queue.get()
						key, value = list(data.items())[0]

						# reboot and shutdown use the same route/key and need an artificial mqtt entry
						# special handling for pressing the reboot button
						# we could also add a shutdown button to shut down the solmate - not implemented so far
						if route == 'shutdown' and value == 'reboot':
							reboot_triggered = True
							response = smws_conn.query_solmate('shutdown', {'shut_reboot': 'reboot'})
							# nothing will executed after a reboot command
							# there will be websocket connection errors due to loss of the connection
							# setting the mqtt operatring state to normal is done in the exception

						# process all other queue elements
						response = smws_conn.query_solmate(route, data)
						if response:
							if 'success' in response and not response['success']:
							# success returned false {'success': False}
								#print(route, data, '\n')
								err = 'Main: Write back to Solmate failed: ' + str(route) + ' ' + str(data)
								sol_utils.logging(err)
								#print('\n')

				# get values from the 'live_values' route
				# we only expect solmate connection exceptions 
				response = smws_conn.query_solmate('live_values', {})
				if response:
					if print_response:
						sol_utils.print_request_response('live_values', response)
					if mqtt_conn:
						mqtt_conn.send_sensor_update_message(response, 'live')

				# get values from the 'get_injection_settings' route if the route is available
				if api_available['hasUserSettings']:
					response = smws_conn.query_solmate('get_injection_settings', {})
					if response:
						if print_response:
							sol_utils.print_request_response('get_injection_settings', response)
						if mqtt_conn:
							mqtt_conn.send_sensor_update_message(response, 'get_injection')

				# get values from the 'get_boost_injection' route if the route is available
				if api_available['sun2plugHasBoostInjection']:
					response = smws_conn.query_solmate('get_boost_injection', {})
					if response:
						if print_response:
							sol_utils.print_request_response('get_boost_injection', response)
						if mqtt_conn:
							mqtt_conn.send_sensor_update_message(response, 'get_boost')

				# check if there is a pending job due like the 'get_solmate_info'
				schedule.run_pending()

				# wait for the next round (async, non blocking for any other running background processes)
				sol_utils.timer_wait('timer_live')

		except Exception as err:
			# error printing has been done in the solmate/mqtt class

			if len(err.args) == 2:
				# if there are 2 arguments in the raised error, we hope we have raised it
				# then we can manually query the result for further processing
				# err.args[0] is the source string returned
				# err.args[1] is the timer string to be used
				error_string = str(err.args[0])

				if error_string not in ['websocket', 'mqtt']:
					# we always have argument [0] but we do not know if it was us
					# log and re-raise to print the trace, ends in exit
					sol_utils.logging('Main: Uncoverabe multi-argument error: ' + str(err))
					raise

				# now we know we are handling own errors
				timer_to_use = str(err.args[1])

				if reboot_triggered:
					# shutdown needs a special timer and not the one coming from the exception
					# because that one is too short and we would finally end up in timer_offline
					timer_to_use = 'timer_reboot'

				seconds_to_wait = str(sol_utils.merged_config[timer_to_use])
				print_string = ' - waiting ' + seconds_to_wait + 's' + ' and reconnect.'

				# for safety, we remove the class object
				# handle exceptions based on the source

				if error_string == 'websocket':
					if smws_conn:
						smws_conn = None
					eet_connected = False
					# the scheduler needs to be reset because the conenction object is no longer valid
					schedule.clear()
					sol_utils.logging('Main: Websocket: Connection error' + print_string)
					# do not process any queue in the timer as long we reestablish the connection
					# set optional argument false, defaults to true
					# note that mqtt may be running but websocket is disconnected
					# this handling is for safety because one could send data via HA to MQTT
					# any open queue elements will be processed after reestablishing the connection !
					sol_utils.timer_wait(timer_to_use, False)
					if reboot_triggered:
						# we must come here because of the connection loss
						# after the timer has ended, go back to normal in mqtt
						mqtt_conn.set_operating_state_normal()
						reboot_triggered = False

				if error_string == 'mqtt':
					# this can only come if mqtt is active 
					if mqtt_conn:
						mqtt_conn = None
					mqtt_connected = False
					sol_utils.logging('Main: MQTT: Connection error' + print_string)
					sol_utils.timer_wait(timer_to_use)

			else:
				# the error was not one of the catched above and therefore not coverable
				# log and re-raise to print the trace, ends in exit
				sol_utils.logging('Main: Uncoverabe single argument error: ' + str(err.args[0]))
				raise

			# continue the while loop and resetup connections
			pass
