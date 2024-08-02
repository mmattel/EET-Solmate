import asyncio
import os
import queue
import sys
import syslog
import solmate_importmanager as sol_im
from datetime import datetime
from importlib import metadata

# functions here are provided for general availability

# create a new queue which can be accessed from all importing modules
# we use it for the communication between mqtt and the main loop
# each element contains a tuple (route, key, value), set by mqtt on message recieved
# this defines updates to be sent to solmate 
mqtt_queue = queue.Queue()

# provide a global available config variable 
merged_config = {}

# properly create an async loop because of a warning popping up with python >=3.10:
# DeprecationWarning: There is no current event loop
# https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.get_event_loop
# https://stackoverflow.com/questions/73884117/how-to-replace-asyncio-get-event-loop-to-avoid-the-deprecationwarning
# https://stackoverflow.com/questions/46727787/runtimeerror-there-is-no-current-event-loop-in-thread-in-async-apscheduler
def create_async_loop():

	try:
		# we first try the old way
		loop = asyncio.get_event_loop()
	except RuntimeError as err:
		# ok, that was not working, do it the new way
		if str(err).startswith('There is no current event loop in thread'):
			loop = asyncio.new_event_loop()
			asyncio.set_event_loop(loop)
		else:
			# if that also not worked, raise the error to track it
			raise
	return loop

def logging(message):
	# print logging data to console (conditional) and syslog (always)
	global merged_config

	# mandatory print the message on the console if defined
	if merged_config['general_console_print']:
		if merged_config['general_console_timestamp']:
			timestamp = '[' + datetime.now().strftime('%Y-%m-%dT%H:%M:%S') + '] '
			print(timestamp + message)
		else:
			print(message)

	# the message maybe not a string but a number, better safe than sorry
	message = str(message)

	if merged_config['internal_access_self'] is None:
		# remove \r = carriage return (octal 015)
		# this would else show up in syslog like as #015Interrupted by keyboard
		# a timestamp is not needed as syslog does that automatically
		message = message.replace('\r', '')
		syslog.syslog(f'{message}')
	else:
		self = merged_config['internal_access_self']
		self.log(message)

async def _async_timer(timer_value):
	# run an async timer
	await asyncio.sleep(timer_value)

def timer_wait(timer_name, process_queue = True):
	# wait the number of seconds passed via the name as argument

	# mqtt_queue is defined on the module level
	global mqtt_queue
	global merged_config

	# wait, but let other tasks like websocket or mqtt do its backend stuff.
	# timer.sleep would hard block that
	# using a range object to count down in steps of half a second
	# by that, we can check the presense for a new queue object (injected by mqtt)
	# if a new queue object was identified, just leave
	for x in range(merged_config[timer_name] * 2):
		# check if the queue has an item to process. in case exit the for loop
		# but only if there is no processing of an mqtt command like reboot
		# there we have already a mqtt_queue item and we must pass the waiting time
		if process_queue:
			# if mqtt is not active, there will also never be an element added to the queue
			if mqtt_queue.qsize() != 0:
				break
		create_async_loop().run_until_complete(_async_timer(0.5))

def print_request_response(route, response):
	# print response in formatted or unformatted json
	# note that the route is always printed to the console in color for ease of readability

	# hardcoded, set to 0 to print unformatted as string
	print_json = 1
	if print_json == 1:
		print('\n' + route + ':')
		# ensure_ascii = False escapes characters like <, >, | etc
		json_formatted_str = json.dumps(response, indent=2, ensure_ascii = False)
		print(json_formatted_str)
	else:
		print(route + ': ' + str(response))

def dynamic_import(pattern, path, query_name, install_name, imports, name_objects):
	# dynamically install and import modules
	# first, get the current package version installed
	# if false we have a lower version, or it is missing at all and we need to do a special
	# install and import. normally the library is installed upfront like when using a	
	# os based install. but when using appdaemon, there may be already a library installed
	# which can be lower and overwriting is not possible. therefore we fetch a custom defined
	# and store/use it on a defined location outside the OS. with that, we can have multiple
	# in parallel not conflicting
	# note that install_name ('paho_mqtt') and query_name (query_name) may not be equal

	response, version, message = sol_im.get_installed_version(query_name, pattern)

	if response:
		# import the default existing one from the OS, it matches the requirement
		try:
			for c in imports:
				exec(c, globals())
		except Exception as err:
			logging('Utils: ' + str(err))
			logging('Utils: Default import error, cant continue, hard exit')
			sys.exit()
	else:
		try:
			# get the highest matching version to install according the given pattern in x
			matching_version = sol_im.get_available_version(query_name, pattern)
			#print(matching_version)
			pth = os.path.join(path, install_name + '_' + matching_version)
			with sol_im.import_helper(install_name, pth):
				#print()
				#print('1. try to install the hopefully downloaded')
				# first try to import related special package(s) - if the package was already installed
				# import will fail if the package was not installed before
				for c in imports:
					#print(c)
					exec(c, globals())

		except Exception as err:
			# install a specific version of the paho-mqtt package into a defined directory
			if version:
				# package found, but version does not match
				message = 'MQTT: Found \'' + query_name + '\' ' + str(version) + ' which is lower than the required.'
				# use the original message from the query above if no package installed in the OS

			logging(message)
			logging('MQTT: Special install of \'' + query_name + '\' ' + matching_version)

			try:
				# install the special package
				sol_im.install_version(install_name, matching_version, pth)

			except Exception as err:
				logging('MQTT: An error occured installing \'' + paho-mqtt + '\' ' + str(version) + ' exiting.')
				logging('MQTT: ' + str(err))
				sys.exit()

			# import this specifiv package version
			with sol_im.import_helper(install_name, pth):
				#print()
				#print('2. try again install the downloaded')
				# then import related special package(s) - the package got installed
				# import will fail if the package was not installed before
				for c in imports:
					#print(c)
					exec(c, globals())

	# after successful importing, return the objects so that the caller can use it
	# because we came here, there are objetcs present and we dont need an exception handling
	return_object = []
	for x in name_objects:
		return_object.append(_get_var_name(x))
		#break
	#sys.exit()
	return return_object

def _get_var_name(variable):
	# get for the variable passed the object found
	for name, value in globals().items():
		#print(name,value)
		if name is variable:
			return value

# though not longer necessary and used, we keep this function. who knows...
def restart_program(counter=0, mqtt=False):
	global merged_config

	# this restarts the program like you would have started it manually again
	# used for events where it is best to start from scratch

	if mqtt:
		# gracefully shut down mqtt first if it was configured
		# it will not raise a kbd interrupt as it was programatically initiated 
		mqtt.graceful_shutdown()

	if counter > 0:
		# log restart reason if _consescutive_ websocket errors occured
		logging('Restarting program due to ' + str(counter) + ' consecutive unprocessable WS conditions.', merged_config)
	else:
		# log that we are restarting without describing the cause
		logging('Restarting program.', merged_config)

	sys.stdout.flush()
	os.execv(sys.executable, ['python'] + sys.argv)
