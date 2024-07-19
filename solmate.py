#!/usr/bin/env python
import os
import sys
import json
import time
import signal
import schedule
from termcolor import colored
from datetime import datetime
import solmate_check as check
import solmate_env as env
import solmate_mqtt as smmqtt
import solmate_utils as utils
import solmate_websocket as smws

# 2024.07
version = '6.1.0'
merged_config = {}

def print_request_response(route, response):
	# print response in formatted or unformatted json
	# note that the route is always printed to the console in color for ease of readability

	# hardcoded, set to 0 to print unformatted as string
	print_json = 1
	if print_json == 1:
		print(colored('\n' + route + ':', 'red'))
		# ensure_ascii = False escapes characters like <, >, | etc
		json_formatted_str = json.dumps(response, indent=2, ensure_ascii = False)
		print(json_formatted_str)
	else:
		print(colored(route + ': ', 'red') + str(response))

def query_once_a_day(smws_conn, route, data, merged_config, mqtt, print_response, endpoint):
	# send request but only when triggered by the scheduler
	# use only for requests with routes that change rarely, more requests can be added
	utils.logging('Once a day queries called by scheduler.', merged_config)
	response = smws_conn.query_solmate(route, data, merged_config, mqtt)
	if response != False:
		if not 'timestamp' in response:
			# fake a timestamp into the response if not present
			response['timestamp'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
		if not 'operating_state' in response:
			# fake an operating_state into the response if not present, the content will be added in mqtt.
			response['operating_state'] = ''
		if print_response:
			print_request_response(route, response)
		if mqtt:
			mqtt.send_sensor_update_message(response, endpoint)

def connect_solmate(merged_config):

	try:
		# Initialize websocket
		# when en error occurs during connenction we wait 'timer_offline', part of the exception
		smws_conn = smws.connect_to_solmate(merged_config)
		# when en error occurs during authentication we wait 'timer_offline', part of the exception
		# here, most likely redirection errors may occur when connecting to the cloud
		response = smws_conn.authenticate()

	except Exception:
		utils.logging('Failed creating connection/authentication to websocket class.', merged_config)
		# re-raise the source error, it containes all necessary data
		raise

	# local
	# check the presense and value for local access
	# if the solmates subdomain is part of the URI
	# local can either be true or false
	if 'eet_local_subdomain' in merged_config:
		# only if the key is configured
		# value_if_true if condition else value_if_false
		local = True if merged_config['eet_local_subdomain'] in merged_config['eet_server_uri'] else False
	else:
		local = False

	# online
	# determine if the system is online
	# when connected to the cloud, you get an 'online' response
	# telling that the solmate is also conected to the server 
	if 'online' in response:
		online = response['online']
		local = False
	# when directly connected to the solmate, there is no response value returned
	# we have to manually define it because we were able to directly connect
	else:
		online = local

	# on startup, log and continue, or restart
	# note that if during processing the solmate goes offline, the connection closes
	# and with the automatic restart procedure, we endup in this questionaire here again
	if online:
		# solmate is online
		utils.logging('SolMate is online.', merged_config)
	else:
		# solmate is not online
		utils.logging('Your SolMate is offline.', merged_config)
		# wait until the next try, but do it with a full restart

	return smws_conn, online, local

def check_routes(merged_config, smws_conn, local):

	# check if we should *only* print the current API info response
	# eases debugging the current published available routes
	if merged_config['general_api_info']:
		response = smws_conn.query_solmate('get_api_info', {}, merged_config)
		print('\n\'get_api_info\' route info requested: \n')
		print(json.dumps(response, ensure_ascii=False, indent=2, separators=(',', ': ')))
		sys.exit()

	# define api routes or behaviours that may not be available depending on the connection
	api_available = {}

	# the name is if seen 1:1 from the webUI, true | false
	# some routes ares only available when connected locally but (currently) not via the cloud
	# check_route returns true if the route exists and false if not
	api_available['sun2plugHasBoostInjection'] = smws_conn.check_route('get_boost_injection', {})
	api_available['hasUserSettings'] = smws_conn.check_route('get_injection_settings', {})

	# the shutdown api has never a true response, we need to decide based on former information
	api_available['shutdown'] = local

	# some routes we know
	api_available['local'] = local

	return api_available

def connect_mqtt(merged_config, api_available):

	if merged_config['general_use_mqtt']:
		# initialize and start mqtt
		try:
			mqtt = smmqtt.solmate_mqtt(merged_config, api_available)
			mqtt.init_mqtt_client()
			# note that signal handling must be done after initializing mqtt
			# else the handler cant gracefully shutdown mqtt.
			# use os.kill(os.getpid(), signal.SIGTERM) where necessary to simulate e.g. a sigterm
			# signal handlers are always executed in the main Python thread of
			# the main interpreter, even if the signal was received in another thread.
			# if not otherwise defined, it itself raises a KeyboardInterrupt to make a shutdown here too
			signal.signal(signal.SIGINT, mqtt.signal_handler_sigint)
			# ctrl-c
			signal.signal(signal.SIGTERM, mqtt.signal_handler_sigterm)
			# sudo systemctl stop eet.solmate.service

		except Exception:
			# either class initialisation or initializing mqtt failed
			# in both cases we cant continue and the the program must end
			raise

	else:
		mqtt = False

	return mqtt

def main(version):

	# get envvars to configure access either from file or from os/docker envvars
	global merged_config
	merged_config = env.process_env(version)

	# get the general program config data
	print_response = merged_config['general_print_response']

	# initialize colors for output, needed for Windows
	if sys.platform == 'win32':
		os.system('color')

    # check for package versions because of breaking changes in libraries used
	check.package_version(merged_config)

	# first validity config check
	if 'eet_server_uri' not in merged_config.keys():
		# if the uri key is not present, exit.
		# if the uri key is present but empty or wrong, the error can and will be catched below
		utils.logging('\'eet_server_uri\' was not defined in the configuration, exiting.', merged_config)
		sys.exit()

	smws_conn = None
	mqtt = None
	eet_connected = False
	mqtt_connected = False
	job_scheduler = False

	while True:
		# because things can always happen, we check connectivity and establish if not connected

		try:
			if not eet_connected:
				# connect and authenticate, don't continue if this fails
				# in case there is no connection, the timer value defines which timer to use
				smws_conn, online, local = connect_solmate(merged_config)
				eet_connected = True
				api_available = check_routes(merged_config, smws_conn, local)

			if not mqtt_connected:
				# connect and authenticate to mqtt if defined
				# mqtt can either be false (mqtt not used) or contains the mqtt connection object
				mqtt = connect_mqtt(merged_config, api_available)
				# mqtt is now either false (dont use mqtt) or contains the mqtt object
				# connected says, that technically initialisation was successful
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
					merged_config=merged_config,
					mqtt=mqtt,
					print_response=print_response,
					endpoint='info'
				)

			# run all already defined tasks in the scheduler to get a first response
			# only necessary to run once even if one of the connections are resetup
			if not job_scheduler:
				schedule.run_all()
				job_scheduler = True

			while True:
			# loop to continuosly request live values or process commands from mqtt

				if mqtt:
					# only if mqtt is enabled
					# process all write requests from the queue initiated by mqtt
					while utils.mqtt_queue.qsize() != 0:
						# we have a message from mqtt because a value change or a button being pressed
						# data can be a multi entry in the dictionary like boost,
						# but for e.g. shutdown it is only one
						route, data = utils.mqtt_queue.get()
						key, value = list(data.items())[0]

						# reboot and shutdown use the same route/key and need an artificial mqtt entry
						# special handling for pressing the reboot button
						# we could also add a shutdown button to shut down the solmate - not implemented so far
						if route == 'shutdown' and value == 'reboot':
							response = smws_conn.query_solmate('shutdown', {'shut_reboot': 'reboot'}, merged_config, mqtt)
							# nothing will executed after a reboot command
							# there will be websocket connection errors due to loss of the connection
							# setting the mqtt operatring state to normal is done in the exception

						# process all other queue elements
						response = smws_conn.query_solmate(route, data, merged_config, mqtt)
						if response:
							# {'success': True}
							if list(response.keys())[0] != 'success':
								#print(route, data, '\n')
								err = 'Write back to Solmate failed: ' + str(route) + ' ' + str(data)
								utils.logging(err, merged_config)
								#print('\n')

				# get values from the 'live_values' route
				# we only expect solmate connection exceptions 
				response = smws_conn.query_solmate('live_values', {}, merged_config, mqtt)
				if response:
					if print_response:
						print_request_response('live_values', response)
					if mqtt:
						mqtt.send_sensor_update_message(response, 'live')

				# get values from the 'get_injection_settings' route if the route is available
				if api_available['hasUserSettings']:
					response = smws_conn.query_solmate('get_injection_settings', {}, merged_config, mqtt)
					if response:
						if print_response:
							print_request_response('get_injection_settings', response)
						if mqtt:
							mqtt.send_sensor_update_message(response, 'get_injection')

				# get values from the 'get_boost_injection' route if the route is available
				if api_available['sun2plugHasBoostInjection']:
					response = smws_conn.query_solmate('get_boost_injection', {}, merged_config, mqtt)
					if response:
						if print_response:
							print_request_response('get_boost_injection', response)
						if mqtt:
							mqtt.send_sensor_update_message(response, 'get_boost')

				# check if there is a pending job due like the 'get_solmate_info'
				schedule.run_pending()

				# wait for the next round (async, non blocking for any other running background processes)
				utils.timer_wait(merged_config, 'timer_live')

		except Exception as err:
			# error printing has been done in the solmate/mqtt class

			if len(err.args) == 2:
				# if there are 2 arguments in the raised error, we know we have raised it
				# manually and can query the result for further processing
				# err.args[0] is the source string returned
				# err.args[1] is the timer string to be used
				error_string = err.args[0]

				if mqtt:
					if route == 'shutdown' and value == 'reboot':
						# shutdown needs a special timer and not the one coming from the exception
						# because that one is too short and we would finally end up in timer_offline
						timer_to_use = 'timer_reboot'
				else:
					timer_to_use = err.args[1]

				seconds_to_wait = merged_config[timer_to_use]
				string = ' - waiting ' + str(seconds_to_wait) + 's' + ' and reconnect.'

				# for safety, we remove the class object

				if error_string == 'websocket':
					if smws_conn:
						smws_conn = None
					eet_connected = False
					# the scheduler needs to be reset because the conenction object is no longer valid
					schedule.clear()
					utils.logging('Websocket connection error' + string, merged_config)
					# do not process any queue in the timer as long we reestablish the connection
					# set optional argument false, defaults to true
					# note that mqtt may be running but websocket is disconnected
					# this handling is for safety because one could send data via HA to MQTT
					# any open queue elements will be processed after reestablishing the connection !
					utils.timer_wait(merged_config, timer_to_use, False)
					if mqtt:
						# after the timer has ended, go back to normal in mqtt
						mqtt.set_operating_state_normal()

				if error_string == 'mqtt':
					# this can only come if mqtt is active 
					if mqtt:
						mqtt = None
					mqtt_connected = False
					utils.logging('MQTT connection error' + string, merged_config)
					utils.timer_wait(merged_config, timer_to_use)
			else:
				# the error was not one of the catched above and therefore not coverable
				# re-raising so it can be handled outside (most likely to exit)
				raise
			# continue the while loop and resetup connections
			pass

if __name__ == '__main__':
	try:
		main(version)
	except Exception:
		# an error has happened before successfully getting the envvars in process_env
		# to avoid running into an error, we define two mandatory envvars for logging, if not present
		merged_config.setdefault('general_console_print', True)
		merged_config.setdefault('general_console_timestamp', False)
		# re-raise the error to be handled
		raise
	except KeyboardInterrupt:
		# avoid printing ^C on the console
		# \r = carriage return (octal 015)
		utils.logging('\rInterrupted by keyboard', merged_config)
		try:
			# terminate script by Control-C, exit code = 130
			sys.exit(130)
		except SystemExit:
			os._exit(130)
	except Exception as err:
		utils.logging(str(err), merged_config)
