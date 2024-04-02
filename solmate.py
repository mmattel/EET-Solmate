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

# version 2.0.0
# 2023.12.10

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

def query_once_a_day(smws_conn, route, data, merged_config, mqtt, smws, print_response, console_print, endpoint):
	# send request but only when triggered by the scheduler
	# use only for requests with routes that change rarely, more requests can be added
	utils.logging('Once a day queries called by scheduler.', console_print)
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

def main():

	# get envvars to configure access either from file or from os/docker envvars
	merged_config = env.process_env()

	# get the general program config data
	add_log = True if merged_config['general_add_log'] == 'True' else False
	print_response = True if merged_config['general_print_response'] == 'True' else False
	console_print = True if merged_config['general_console_print'] == 'True' else False
	use_mqtt = True if merged_config['general_use_mqtt'] == 'True' else False

	# initialize colors for output, needed for Windows
	if sys.platform == 'win32':
		os.system('color')

    # check for package versions because of breaking changes in libraries used
	check.package_version(console_print)

	# connect and authenticate, don't continue if this fails
	if 'eet_server_uri' not in merged_config.keys():
		# if the uri key is not present, exit.
		# if the uri key is present but empty or wrong, the error can and will be catched below
		utils.logging('\'eet_server_uri\' was not defined in the configuration, exiting.', console_print)
		sys.exit()

	try:
		# Initialize websocket
		smws_conn = smws.connect_to_solmate(merged_config, console_print)
		response = smws_conn.authenticate()
	except Exception as err:
		utils.logging('Failed creating connection/authentication to websocket class.', console_print)
		# wait until the next try, but do it with a full restart
		utils.timer_wait(merged_config, 'timer_offline', console_print, True)
		utils.restart_program(console_print)

	# check the precense and value for local access
	# if the solmates subdomain is part of the URI
	if 'eet_local_subdomain' in merged_config:
		# only if the key is configured
		# value_if_true if condition else value_if_false
		local = True if merged_config['eet_local_subdomain'] in merged_config['eet_server_uri'] else False
	else:
		local = False

	# determine if the system is online
	# when connected to the server, you get a 'online' response
	# telling that the solmate is also conected to the server 
	if 'online' in response:
		online = response['online']
		local = False
	# when directly connected to the solmate, there is no response value returned
	# we have to manually define it manually because we were able to directly connect
	else:
		online = local

	# on startup, log and continue, or restart
	# note that if during processing the solmate goes offline, the connection closes
	# and with the automatic restart procedure, we endup in this questionaire here again
	if online:
		# solmate is online
		utils.logging('SolMate is online.', console_print)
	else:
		# solmate is not online
		utils.logging('Your SolMate is offline.', console_print)
		# wait until the next try, but do it with a full restart
		utils.timer_wait(merged_config, 'timer_offline', console_print, True)
		utils.restart_program(console_print)

	# check if we should *only* print the current API info response
	if 'general_api_info' in merged_config.keys():
		# if the api_info key is present check for True:
		if merged_config['general_api_info'] == 'True':
			response = smws_conn.query_solmate('get_api_info', {}, merged_config)
			print('\n\'get_api_info\' route info requested: \n')
			print(json.dumps(response, ensure_ascii=False, indent=2, separators=(',', ': ')))
			sys.exit()

	if use_mqtt:
		# initialize and start mqtt
		mqtt = smmqtt.solmate_mqtt(merged_config, smws_conn, local, console_print)
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
	# arguments: conn, route, data, merged_config, mqtt, smws, print_response
	schedule.every().day.at('23:45').do(
			query_once_a_day,
			smws_conn=smws_conn,
			route='get_solmate_info',
			data={},
			merged_config=merged_config,
			mqtt=mqtt,
			smws=smws,
			print_response=print_response,
			console_print=console_print,
			endpoint='info'
		)

	# run all already defined tasks in the scheduler to get a first response
	schedule.run_all()

	while True:
	# loop to continuosly request live values or process commands from mqtt

		if mqtt and utils.mqueue.qsize() != 0:
			# if we have a message from mqtt because a button was pressed like reboot
			message = utils.mqueue.get()
			# here we can distinguish different messages to process.
			# 'shutdown' would be possible if catched by mqtt
			if message == 'reboot':
				response = smws_conn.query_solmate('shutdown', {'shut_reboot': 'reboot'}, merged_config, mqtt)
				if response != False:
					# if there is a response from the reboot command, print it
					utils.logging(str(response), console_print)
				# this gets only processed if websocket stays connected despite the reboot command
				# which would drop it (reboot was not accepted), better safe than sorry
				utils.timer_wait(merged_config, 'timer_reboot', console_print, False, True)
				mqtt.set_operating_state_normal()

		# query_solmate(route, value, merged_config, mqtt)
		response = smws_conn.query_solmate('live_values', {}, merged_config, mqtt)

		if response != False:
			if print_response:
				print_request_response('live_values', response)
			if mqtt:
				mqtt.send_sensor_update_message(response, 'live')

		# check if there is a pending job due
		schedule.run_pending()

		# wait for the next round (async, non blocking for any other running background processes)
		utils.timer_wait(merged_config, 'timer_live', console_print, False)

	if mqtt:
		# whyever we came here, but to be fail safe,
		# make a graceful shutdown, but do not raise a signal, the program terminated "normally".
		mqtt.graceful_shutdown()

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		# avoid printing ^C on the console
		# \r = carriage return (octal 015)
		utils.logging('\rInterrupted by keyboard', True)
		try:
			# terminate script by Control-C, exit code = 130
			sys.exit(130)
		except SystemExit:
			os._exit(130)
