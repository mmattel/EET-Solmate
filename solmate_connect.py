import sys
import signal
import solmate_utils as utils
import solmate_websocket as smws

# code that connects to the respective classes and returns the connection object
# return solmate connection dependent api routes

def connect_solmate():
	# connect to the solmate via websocket

	try:
		# Initialize websocket
		# when en error occurs during connenction, we wait 'timer_offline', part of the exception
		smws_conn = smws.connect_to_solmate()
		# when en error occurs during authentication we hard stop - the pwd is wrong
		response = smws_conn.authenticate()

	except Exception as err:
		# here, most likely redirection or hash errors occur when connecting to the cloud
		utils.logging('Websocket: Failed creating connection/authentication to class.')
		# re-raise the error, it will lead to a retry as it maybe a temporary issue
		raise

	# local
	# check the presense and value for local access
	# if the solmates subdomain is part of the URI
	# local can either be true or false
	if 'eet_local_subdomain' in utils.merged_config:
		# only if the key is configured
		# value_if_true if condition else value_if_false
		local = True if utils.merged_config['eet_local_subdomain'] in utils.merged_config['eet_server_uri'] else False
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
		utils.logging('Websocket: SolMate is online')
	else:
		# solmate is not online
		utils.logging('Websocket: Your SolMate is offline')
		# wait until the next try, but do it with a full restart

	return smws_conn, online, local

def connect_mqtt(api_available):
	# connect to the mqtt broker

	# IMPORTANT: import the module here because we need to have 'solmate_env' executed first !
	# if imported in main, the code outside the class in 'solmate_mqtt' will get executed missing data 
	import solmate_mqtt as smmqtt

	if utils.merged_config['general_use_mqtt']:
		# initialize and start mqtt
		try:
			mqtt_conn = smmqtt.solmate_mqtt(api_available)
			mqtt_conn.init_mqtt_client()
			# note that signal handling must be done after initializing mqtt
			# else the handler cant gracefully shutdown mqtt.
			# use os.kill(os.getpid(), signal.SIGTERM) where necessary to simulate e.g. a sigterm
			# signal handlers are always executed in the main Python thread of
			# the main interpreter, even if the signal was received in another thread.
			# if not otherwise defined, it itself raises a KeyboardInterrupt to make a shutdown here too
			signal.signal(signal.SIGINT, mqtt_conn.signal_handler_sigint)
			# ctrl-c
			signal.signal(signal.SIGTERM, mqtt_conn.signal_handler_sigterm)
			# sudo systemctl stop eet.solmate.service

		except Exception as err:
			# either class initialisation or initializing mqtt failed
			# in both cases we cant continue and the the program must end
			raise

	else:
		mqtt_conn = False

	return mqtt_conn

def check_routes(smws_conn, local):

	# check if we should *only* print the current API info response
	# eases debugging the current published available routes
	if utils.merged_config['general_api_info']:
		response = smws_conn.query_solmate('get_api_info', {})
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
