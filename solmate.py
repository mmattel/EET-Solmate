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

# version 1.1.2
# 2023.09.02

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

	# log timer calls. set to false if all works and you just loop thru the live values
	# to avoid polluting syslog with data  
	add_log = False

	# enable/disable printing _response_ data to the console, useful for testing
	print_response = False

	# print logging data to console (conditional) and syslog (always)
	# the value is optional and defaults to False
	console_print = True

	# globally enable/disable mqtt, makes it easier for testing
	use_mqtt = True

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
		smws.logging('Failed creating connection/authentication to websocket class.', console_print)
		# wait until the next try, but do it with a full restart
		smws.timer_wait(timer_config, 'timer_offline', console_print, True)
		smws_conn.restart_program()

	# determine if the system is online
	if 'online' in response:
		online = response['online']
	elif 'sol.eet.energy' in solmate_config['eet_server_uri']:
		online = True
	else:
		online = False

	# on startup, log and continue, or restart
	# note that if during processing the solmate goes offline, the connection closes
	# and with the automatic restart procedure, we endup in this questionaire here again
	if online:
		# solmate is online
		smws.logging('SolMate is online.', console_print)
	else:
		# solmate is not online
		smws.logging('Your SolMate is offline.', console_print)
		# wait until the next try, but do it with a full restart
		smws.timer_wait(timer_config, 'timer_offline', console_print, True)
		smws_conn.restart_program()

	if use_mqtt:
		# initialize and start mqtt
		mqtt = smmqtt.solmate_mqtt(mqtt_config, smws, console_print)
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
			if print_response:
				print_request_response('live_values', response)
			if mqtt:
				mqtt.send_update_message(response, 'live')

		# check if there is a pending job due
		schedule.run_pending()

		# wait for the next round
		smws.timer_wait(timer_config, 'timer_live', console_print, False)

	if mqtt:
		# make a graceful shutdown, but do not raise a signal, the program terminated "normally" 
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
