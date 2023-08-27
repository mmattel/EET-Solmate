#!/usr/bin/env python
import os
import sys
import json
import time
import signal
import schedule
from termcolor import colored
from datetime import datetime
import solmate_env as env
import solmate_mqtt as smmqtt
import solmate_websocket as smws

# version 1.0
# 2023.08.27

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

def query_once_a_day(smws_conn, route, data, timer_config, mqtt, smws, print_response, console_print, endpoint):
	# send request but only when triggered by the scheduler
	# use only for requests with routes that change rarely, more requests can be added
	smws.logging('Once a day queries called by scheduler.', console_print)
	response = smws_conn.query_solmate(route, data, timer_config, mqtt)
	if response != False:
		if not 'timestamp' in response:
			# fake a timestamp into the response if not present
			response['timestamp'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
		if print_response:
			print_request_response(route, response)
		if mqtt:
			mqtt.send_update_message(response, endpoint)

def main():

	# catch ctrl-c
	# the signal handler must be here because we need to access mqtt
	# it itself raises a KeyboardInterrupt to make a shutdown here too
	def signal_handler(signum, frame):
		mqtt.graceful_shutdown()

	# log timer calls. set to false if all works and you just loop thru the live values
	# to avoid polluting syslog with data  
	add_log = True

	# enable/disable printing _response_ data to the console, useful for testing
	print_response = False

	# print logging data to console (conditional) and syslog (always)
	# the value is optional and defaults to False
	console_print = True

	# globally enable/disable mqtt, makes it easier for testing
	enable_mqtt = True

	# initialize colors for output, needed for Windows
	if sys.platform == 'win32':
		os.system('color')

	# get envvars to configure access either from file or from os/docker envvars
	mqtt_config, solmate_config, timer_config = env.process_env(smws)

	# connect and authenticate, dont continue if this fails
	if 'eet_server_uri' not in solmate_config.keys():
		# if the uri key is not present, exit.
		# if the uri key is present but empty or wrong, the error can and will be catched below
		smws.logging('\'eet_server_uri\' was not defined in the configuration, exiting.', console_print)
		sys.exit()

	try:
		# Initialize websocket
		smws_conn = smws.connect_to_solmate(solmate_config, console_print)
		response = smws_conn.authenticate()
	except Exception as err:
		smws.logging('Failed creating connection to websocket class.', console_print)
		smws.logging(str(err), console_print)
		sys.exit()

	# determine if the system is online
	if 'online' in response:
		online = response['online']
	elif solmate_config['eet_network'] == 'local':
		online = True
	else:
		online = False

	# log and continue, or restart
	if online:
		# solmate is online
		smws.logging('SolMate is online.', console_print)
	else:
		# solmate is not online
		smws.logging('Your SolMate is offline.', console_print)
		# wait until the next try, but do it with a full restart
		smws.timer_wait(timer_config, 'timer_offline', console_print, add_log)
		smws_conn.restart_program()

	if enable_mqtt:
		# initialize and start mqtt
		mqtt = smmqtt.solmate_mqtt(mqtt_config, smws, console_print)
		mqtt.init_mqtt_client()
		# note that doing a signal handling for ctrl-c must be done after initializing mqtt
		# else the handler cant gracefully shutdown
		signal.signal(signal.SIGINT, signal_handler)
	else:
		mqtt = False

	# start a scheduler for once-a-day requests like the 'get_solmate_info',
	# this content changes rarely, most likely the version number from time to time.
	# arguments: conn, route, data, timer_config, mqtt, smws, print_response
	schedule.every().day.at('23:45').do(
			query_once_a_day,
			smws_conn=smws_conn,
			route='get_solmate_info',
			data={},
			timer_config=timer_config,
			mqtt=mqtt,
			smws=smws,
			print_response=print_response,
			console_print=console_print,
			endpoint='info'
		)

	# run all already defined tasks in the scheduler to get a first response
	schedule.run_all()

	while True:
	# loop to continuosly request live values

		# query_solmate(route, value, timer_config, mqtt)
		response = smws_conn.query_solmate('live_values', {}, timer_config, mqtt)

		if response != False:
			# if the response was false, we just continue
			# note that 'inject_energy' is an artificial value that derives from:
			# inject_energy = inject_power [W] * timer_live [s] / 3600 / 1000 (to bring it into kWh)
			# this simulates a yield per interval that can be shown as statistics in HA,
			# defined in construct_ha_config_message
			kwh = float(
				response['inject_power'] * 
				timer_config['timer_live'] / 3600 / 1000
				)
			# make the response printed in standard and not scientific format with the same number of digits
			response['inject_energy'] = str(f'{kwh:.14f}')
			if print_response:
				print_request_response('live_values', response)
			if mqtt:
				mqtt.send_update_message(response, 'live')

		# wait for the next round
		smws.timer_wait(timer_config, 'timer_live', console_print, False)

	if mqtt:
		mqtt.graceful_shutdown()

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		# avoid printing ^C on the console
		# \r = carriage return (octal 015)
		smws.logging('\rInterrupted by keyboard', True)
		try:
			# terminate script by Control-C, exit code = 130
			sys.exit(130)
		except SystemExit:
			os._exit(130)
