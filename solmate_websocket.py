import asyncio
import time
import websockets
import base64
import hashlib
import json
import sys
import os
import syslog

# the functions outside the class are provided here for general availability

def logging(message, console_print = False):
	# print logging data to console (conditional) and syslog (always)

	if console_print:
		print(message)

	message = message.replace('\r', '')
	# remove \r = carriage return (octal 015)
	# this would else show up in syslog like as #015Interrupted by keyboard
	syslog.syslog(f'{message}')

def timer_wait(timer_config, timer_name, console_print, add_log = True):
	# wait the number of seconds passed via the name as argument

	if add_log:
		# log at all, but decide where
		logging('Waiting: ' + timer_name + ': ' + str(timer_config[timer_name]) + 's', console_print)

	time.sleep(timer_config[timer_name])

class connect_to_solmate:
	# the class managing the connection to solmate (server or local)

	server_uri= ''                              # the endpoint
	websocket = None                            # websocket will be stored here
	message_id = 0                              # continous message id

	def __init__(self, solmate_config, console_print):
		self.solmate_config=solmate_config
		self.server_uri = solmate_config['eet_server_uri']
		self.count_before_restart = 0
		self.console_print = console_print
		# set of mandatory keywords in the query response if the endpoint does not exist
		self.err_kwds = {'Response:', 'NotImplemetedError'}

		logging('Initializing websocket connection...', self.console_print)

	def redirected_server(self, uri):
		self.server_uri = uri

	async def create_socket(self):
		# create a websocket and connect it to the endpoint.
		try:
			self.websocket = await websockets.connect(self.server_uri)
			# you may want to add additional connect parameters like 'ping_interval=xxx' and 'ping_timeout=xxx'
			# see the readme.md file for a possible reason
			logging('Websocket is connected to: ' + self.server_uri, self.console_print)
		except Exception as err:
			logging('Websockets: ' + str(self.server_uri), self.console_print)
			logging('Websockets: ' + str(err), self.console_print)
			raise

	async def send_api_request(self, data):
		# send an api request with the given data and return response data.
		try:
			self.message_id += 1
			await self.websocket.send(json.dumps(data))
			response = json.loads(await self.websocket.recv())

		# specific, when the connection got closed
		except websockets.exceptions.ConnectionClosedOK:
			# closing a connection can occur at any time after successful authentication
			# like when the network times out or the solmate shuts off
			# when a mandatory option is not sent correctly/at all (route=logs, missing parameter),
			# solmate just closes the connection instead writing an error response that could be covered
			# sadly, the error message is not quite helpful as the connection itself was ok
			logging('Request: Connection closed unexpectedly.', self.console_print)
			raise ConnectionError('Connection closed unexpectedly.', self.console_print)

		# for all undefined websocket exceptions
		except Exception as err:
			logging('WS undefined error when requesting: ' + str(err), self.console_print)
			raise

		# return the response
		if 'data' in response:
			return response['data']

		# raise exceptions based on that there was a response but it has issues
		elif 'error' in response:
			# contains the original websocket error data
			err = 'Response: ' + str(response['error'])
			logging(err, self.console_print)
			raise Exception(err)
		else:
			err = 'The response did not contain any useful data.'
			logging(err, self.console_print)
			raise Exception(err)

	def authenticate(self):
		# authenticate on the server or solmate with the given serial number, password and device id
		logging('Authenticating...', self.console_print)
	
		# create and connect to websocket
		try:
			asyncio.get_event_loop().run_until_complete(self.create_socket())
		except Exception:
			# the reason for the exception has been logged already, just exit
			raise

		try:
			# get the response to the request of the login route with the login data
			# note to expect that the endpoint 'login' exists
			response = asyncio.get_event_loop().run_until_complete(self.send_api_request(
				{
					'id': self.message_id,
					'route': 'login',
					'data': {
						'serial_num': self.solmate_config['eet_serial_number'],
						'user_password_hash': base64.encodebytes(hashlib.sha256(self.solmate_config['eet_password'].encode()).digest()).decode(),
						'device_id': self.solmate_config['eet_device_id']
					}
				}
			))

			# if login was successful, get the hash to use for authenticated requests
			if 'success' in response and response['success'] and 'signature' in response:
				# Get the signature for the session
				signature = response['signature']

				# check if Server redirects to another instance
				# (on first connect, the connenction is established to a load-balancer)
				correct_server = False
				while not correct_server:
					# get the response to the authentication route with the authentication data
					response = asyncio.get_event_loop().run_until_complete(self.send_api_request(
						{
							'id': self.message_id,
							'route': 'authenticate',
							'data': {
								'serial_num': self.solmate_config['eet_serial_number'],
								'signature': signature,
								'device_id': self.solmate_config['eet_device_id']
							}
						}
					))

					# handle load-balancer redirect, if there is one
					if 'redirect' in response and response['redirect'] is not None:
						redirect_uri = str(response['redirect'])
						logging('Got redirected to: ' + redirect_uri, self.console_print)
						self.redirected_server(redirect_uri)
						asyncio.get_event_loop().run_until_complete(self.create_socket())
					else:
						# when there is no redirect parameter, the socket is connected to the correct instance
						correct_server = True

				# return the authenticated connection
				logging('Authentication successful!', self.console_print)
				return response
			# authentication failed
			# the reason may be bad credentials or a failure when redirecting
			raise

		except Exception:
			# return that authentication failed
			logging('Authentication failed!', self.console_print)
			raise

	def ws_request(self, route, data):
		# send request for the given route without error handling

		response = asyncio.get_event_loop().run_until_complete(
			self.send_api_request(
				{'id': self.message_id, 'route': route, 'data': data}
			)
		)
		return response

	def query_solmate(self, route, value, timer_config, mqtt):
		# send request for the given route including error handling

		try: 
			x = self.ws_request(route, value)
			# response was successful, reset counter
			self.count_before_restart = 0
			return x

		except ConnectionError:
			# if a connection error happened, restart the program after waiting the timer_conn_err time
			# note that a connection error can also occur when a required parameter is not sent
			# also see 'send_api_request()'
			timer_wait(timer_config, 'timer_conn_err', self.console_print, True)
			self.restart_program(mqtt)

		except Exception as err:
			# depending on other exceptions do

			if len(self.err_kwds & set(str(err).replace(',', '').replace("'", '').split())) == len(self.err_kwds):
				# check if both keywords exist in the error message
				# in case, stop script if the endpoint does not exists, continue makes no sense
				# logging of which inexistent route was already done in 'send_api_request'
				logging('Exiting.', self.console_print)
				sys.exit()
			else:
				# the endpoint existed, but the response was malformed
				if 'sent 1011 (unexpected error) keepalive ping timeout' in str(err):
					# the websocket keep alive ping/pong failed (see readme.md), restart program immediately
					logging('Keep alive ping/pong failed.', self.console_print)
					self.restart_program(mqtt)

				self.count_before_restart += 1
				if self.count_before_restart == timer_config['timer_attempt_restart']:
					# only on _consecutive_ unidentified issues
					# if waiting the response time did not help, restart after the n-th try 
					logging('Too many failed consecutive request attempts: ' + str(self.count_before_restart), self.console_print)
					self.restart_program(mqtt)
				else:
					# the false response tells the caller about the incident, it is handled there
					logging('An unknown but non breaking error happened, continueing.', self.console_print)
					return False

	def restart_program(self, mqtt=False):
		# this restarts the program like you would have started it manually again
		# used for events where it is best to start from scratch

		if mqtt:
			# gracefully shut down mqtt first if it was configured and do not raise a kbd interrupt
			mqtt.graceful_shutdown(False)

		if self.count_before_restart > 0:
			# print restart reason if _consescutive_ websocket errors occured
			logging('Restarting program due to ' + str(self.count_before_restart) + ' consecutive unprocessable WS conditions.', self.console_print)

		sys.stdout.flush()
		os.execv(sys.executable, ['python'] + sys.argv)
