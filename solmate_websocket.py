import asyncio
import base64
import hashlib
import json
import os
import sys
import syslog
import time
import websockets.client
import solmate_utils as utils

class connect_to_solmate:
	# the class managing the connection to solmate (server or local)
	# https://websockets.readthedocs.io/en/stable/reference/asyncio/client.html

	server_uri= ''                              # the endpoint
	websocket = None                            # websocket will be stored here
	message_id = 0                              # continous message id

	def __init__(self, merged_config, console_print):
		self.merged_config=merged_config
		self.server_uri = self.merged_config['eet_server_uri']
		self.count_before_restart = 0
		self.console_print = console_print
		# set of mandatory keywords in the query response if the endpoint does not exist
		self.err_kwds = {'Response:', 'NotImplemetedError'}

		utils.logging('Initializing websocket connection.', self.console_print)
		self._create_websocket()

	def _redirected_server(self, uri):
		self.server_uri = uri

	def _create_websocket(self):
			# create and connect to websocket
		try:
			asyncio.get_event_loop().run_until_complete(self._create_socket())
		except Exception:
			# the reason for the exception has been logged already, just exit
			raise

	async def _create_socket(self):
		# create a websocket and connect it to the endpoint.
		try:
			utils.logging('Create Socket.', self.console_print)
			self.websocket = await websockets.client.connect(self.server_uri)
			# you may want to add additional connect parameters like 'ping_interval=xxx' and 'ping_timeout=xxx'
			# see the readme.md file for a possible reason
			utils.logging('Websocket is connected to: ' + self.server_uri, self.console_print)
		except Exception as err:
			utils.logging('Websockets error: ' + str(self.server_uri), self.console_print)
			utils.logging('Websockets error: ' + str(err) or 'Empty error string returned.', self.console_print)
			raise

	async def _send_api_request(self, data):
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
			utils.logging('Request: Connection closed unexpectedly.', self.console_print)
			raise ConnectionError('Connection closed unexpectedly.', self.console_print)

		# for all undefined websocket exceptions
		except Exception as err:
			utils.logging('Undefined WS error requesting the solmate API: ' + str(err), self.console_print)
			raise

		# return the response
		if 'data' in response:
			return response['data']

		# raise exceptions based on that there was a response but it has issues
		elif 'error' in response:
			# contains the original websocket error data
			err = 'Response: ' + str(response['error'])
			utils.logging(str(err), self.console_print)
			raise Exception(err)
		else:
			err = 'The response did not contain any useful data.'
			utils.logging(str(err), self.console_print)
			raise Exception(err)

	def ws_request(self, route, data, mqtt):
		# send request for the given route without error handling

		try:
			response = asyncio.get_event_loop().run_until_complete(
				self._send_api_request(
					{'id': self.message_id, 'route': route, 'data': data}
				)
			)
			return response

		except RuntimeError as err:
			# an asyncio event loop is thread-specific
			# if there is a thread error, access was out of the current thread!
			# with such an error, we safely restart the program
			utils.logging('Error: ' + str(err), self.console_print)
			utils.restart_program(self.console_print, 0, mqtt)

	def authenticate(self):
		# authenticate on the server or solmate with the given serial number, password and device id
		try:
			# get the response to the request of the login route with the login data
			# note to expect that the endpoint 'login' exists
			utils.logging('Authenticating.', self.console_print)
			response = asyncio.get_event_loop().run_until_complete(self._send_api_request(
				{
					'id': self.message_id,
					'route': 'login',
					'data': {
						'serial_num': self.merged_config['eet_serial_number'],
						'user_password_hash': base64.encodebytes(hashlib.sha256(self.merged_config['eet_password'].encode()).digest()).decode(),
						'device_id': self.merged_config['eet_device_id']
					}
				}
			))

			# if login was successful, get the hash to use for authenticated requests
			if 'success' in response and response['success'] and 'signature' in response:
				# Get the signature for the session to be reused for the next step instead of the password
				signature = response['signature']

				# check if Server redirects to another instance
				# (on first connect, the connenction is established to a load-balancer)
				correct_server = False
				while not correct_server:
					# get the response to the authentication route with the authentication data
					response = asyncio.get_event_loop().run_until_complete(self._send_api_request(
						{
							'id': self.message_id,
							'route': 'authenticate',
							'data': {
								'serial_num': self.merged_config['eet_serial_number'],
								'signature': signature,
								'device_id': self.merged_config['eet_device_id']
							}
						}
					))

					# handle load-balancer redirect, if there is one
					if 'redirect' in response and response['redirect'] is not None:
						redirect_uri = str(response['redirect'])
						utils.logging('Got redirected to: ' + redirect_uri, self.console_print)
						self._redirected_server(redirect_uri)
						asyncio.get_event_loop().run_until_complete(self._create_socket())
					else:
						# when there is no redirect parameter, the socket is connected to the correct instance
						correct_server = True

				# return the authenticated connection
				utils.logging('Authentication successful!', self.console_print)
				return response

			# authentication failed
			# the reason may be bad credentials or a failure when redirecting
			raise
			utils.logging('Authentication failed!', self.console_print)

		except Exception:
			# return that authentication failed
			utils.logging('Authentication failed!', self.console_print)
			raise

	def query_solmate(self, route, value, merged_config, mqtt):
		# send request for the given route including error handling

		try: 
			response = self.ws_request(route, value, mqtt)
			# request was successful, reset counter
			self.count_before_restart = 0
			return response

		except ConnectionError:
			# if a connection error happened, restart the program after waiting the timer_conn_err time
			# note that a connection error can also occur when a required parameter is not sent
			# also see '_send_api_request()'
			utils.timer_wait(merged_config, 'timer_conn_err', self.console_print, True)
			utils.restart_program(self.console_print, 0, mqtt)

		except Exception as err:
			# depending on other exceptions do

			if len(self.err_kwds & set(str(err).replace(',', '').replace("'", '').split())) == len(self.err_kwds):
				# inexistent route
				# check if both keywords exist in the error message
				# in case, stop script if the endpoint does not exists, continue makes no sense
				# logging of which inexistent route was already done in '_send_api_request'
				utils.logging('Exiting.', self.console_print)
				sys.exit()

			if 'sent 1011 (unexpected error) keepalive ping timeout' in str(err):
				# the endpoint existed, but the response was malformed
				# the websocket keep alive ping/pong failed (see readme.md), restart program immediately
				utils.logging('Keep alive ping/pong failed.', self.console_print)
				utils.restart_program(self.console_print, 0, mqtt)

			self.count_before_restart += 1

			if self.count_before_restart == merged_config['timer_attempt_restart']:
				# only on _consecutive_ unidentified issues
				# if waiting the response time did not help, restart after the n-th try 
				utils.logging('Too many failed consecutive request attempts: ' + str(self.count_before_restart), self.console_print)
				utils.restart_program(self.console_print, self.count_before_restart, mqtt)

			utils.logging('An non breaking error happened, continuing.', self.console_print)
			utils.logging('Error: ' + str(err), self.console_print)
			# the false response tells the caller about the incident, it is handled there
			return False
