import asyncio
import os
import queue
import sys
import semver
import syslog
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

# this is just a preparation if the the deprecation would pop up, but has currently NO
# effect and uses the default method of asyncio.get_event_loop()
# tests have shown that it breaks the 'if' code as any request to the solmate runs thru
# self.websocket.recv() which hangs forever if enabled.
#
# properly create an async loop because of a warning popping up with python >=3.10:
# DeprecationWarning: There is no current event loop
# https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.get_event_loop
# https://stackoverflow.com/questions/73884117/how-to-replace-asyncio-get-event-loop-to-avoid-the-deprecationwarning
def create_async_loop():
	# comment/remove when self.websocket.recv() is fixed
	loop = asyncio.get_event_loop()
	return loop

	# do not run this until clarified why self.websocket.recv() hangs forever
	if sys.version_info < (3, 10):
		loop = asyncio.get_event_loop()
	else:
		try:
			loop = asyncio.get_running_loop()
		except RuntimeError:
			loop = asyncio.new_event_loop()
		asyncio.set_event_loop(loop)
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

	message = str(message)
	# the message maybe not a string but a number
	message = message.replace('\r', '')
	# remove \r = carriage return (octal 015)
	# this would else show up in syslog like as #015Interrupted by keyboard
	# a timestamp is not needed as syslog does that automatically
	syslog.syslog(f'{message}')

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
		print(colored('\n' + route + ':', 'red'))
		# ensure_ascii = False escapes characters like <, >, | etc
		json_formatted_str = json.dumps(response, indent=2, ensure_ascii = False)
		print(json_formatted_str)
	else:
		print(colored(route + ': ', 'red') + str(response))

def package_version(package, required_version):
	# https://discuss.python.org/t/the-fastest-way-to-make-a-list-of-installed-packages/23175/4
	# note that due to a "bug" in the importlib version in python 3.9,
	# we cant list installed packages, we can only query them if known.

	found_version = semver.Version.parse(metadata.version(package))

	positions = required_version.split(".")
	message = package + ' ' + str(found_version) + ' found, must be version ' + required_version + '. Check the requirements in README.md, exiting.'

	if len(positions) >= 1:
		if found_version.major != int(positions[0]):
			return False, found_version, message

	if len(positions) >= 2:
		if found_version.minor != int(positions[1]):
			return False, found_version, message

	if len(positions) >= 3:
		if found_version.patch != int(positions[2]):
			return False, found_version, message

	return True, found_version, ""

def restart_program(counter=0, mqtt=False):
	# though not longer necessary and used, we keep this function. who knows...
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

