import asyncio
import os
import queue
import sys
import syslog
import time

# functions here are provided for general availability

# create a new queue which is used from all importing modules
mqueue = queue.Queue()

def logging(message, console_print = False):
	# print logging data to console (conditional) and syslog (always)

	if console_print:
		print(message)

	message = str(message)
	# the message maybe not a string but a number
	message = message.replace('\r', '')
	# remove \r = carriage return (octal 015)
	# this would else show up in syslog like as #015Interrupted by keyboard
	syslog.syslog(f'{message}')

async def _async_timer(timer_value):
	# run an async timer
	await asyncio.sleep(timer_value)

def timer_wait(merged_config, timer_name, console_print, add_log = True, mqtt_command = False):
	# wait the number of seconds passed via the name as argument

	# mqueue is defined on the module level
	global mqueue

	if add_log:
		# log at all, but decide where
		logging('Waiting: ' + timer_name + ': ' + str(merged_config[timer_name]) + 's', console_print)

	# wait, but let other tasks like websocket or mqtt do its backend stuff.
	# timer.sleep would hard block that
	# using a range object to count down in steps of half a second
	# by that, we can check the presense for a new queue object (injected by mqtt)
	# if a new queue object was identified, just leave
	for x in range(merged_config[timer_name] * 2):
		# check if the queue has an item to process. in case exit the for loop
		# but only if there is no processing of an mqtt command like reboot
		# there we have already a mqueue item and we must pass the waiting time 
		if mqtt_command == False:
			if mqueue.qsize() != 0:
				break
		asyncio.get_event_loop().run_until_complete(_async_timer(0.5))

def restart_program(console_print, counter=0, mqtt=False):
	# this restarts the program like you would have started it manually again
	# used for events where it is best to start from scratch

	if mqtt:
		# gracefully shut down mqtt first if it was configured
		# it will not raise a kbd interrupt as it was programatically initiated 
		mqtt.graceful_shutdown()

	if counter > 0:
		# log restart reason if _consescutive_ websocket errors occured
		logging('Restarting program due to ' + str(counter) + ' consecutive unprocessable WS conditions.', console_print)
	else:
		# log that we are restarting without describing the cause
		logging('Restarting program.', console_print)

	sys.stdout.flush()
	os.execv(sys.executable, ['python'] + sys.argv)
