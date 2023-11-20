import asyncio
import os
import sys
import syslog
import time

# functions here are provided for general availability

def logging(message, console_print = False):
	# print logging data to console (conditional) and syslog (always)

	if console_print:
		print(message)

	message = message.replace('\r', '')
	# remove \r = carriage return (octal 015)
	# this would else show up in syslog like as #015Interrupted by keyboard
	syslog.syslog(f'{message}')

async def async_timer(timer_value):
	# run an async timer
	await asyncio.sleep(timer_value)

def timer_wait(merged_config, timer_name, console_print, add_log = True):
	# wait the number of seconds passed via the name as argument

	if add_log:
		# log at all, but decide where
		logging('Waiting: ' + timer_name + ': ' + str(merged_config[timer_name]) + 's', console_print)

	# wait, but let websocket do its backend tasks.
	# timer.sleep would hard block stuff
	asyncio.get_event_loop().run_until_complete(async_timer(merged_config[timer_name]))

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
