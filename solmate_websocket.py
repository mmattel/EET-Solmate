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
	# the class managing the connection to solmate (cloud or local)
	# https://websockets.readthedocs.io/en/stable/reference/asyncio/client.html

	server_uri= ''                              # the endpoint
	websocket = None                            # websocket will be stored here
	message_id = 0                              # continous message id

	def __init__(self, merged_config):
		self.merged_config=merged_config
		self.server_uri = self.merged_config['eet_server_uri']
		self.count_before_restart = 0
		self.message_id = 0
		self.websocket = None
		# set of mandatory keywords in the query response if the endpoint does not exist
		self.err_kwds = {'Response:', 'NotImplemetedError'}

		utils.logging('Initializing websocket connection.', self.merged_config)
		self._create_websocket()

	def _redirected_server(self, uri):
		self.server_uri = uri

	def _create_websocket(self):
		# create and connect to websocket
		try:
			utils.create_async_loop().run_until_complete(self._create_socket())
		except Exception:
			# the reason for the exception has been logged already, just exit
			raise

	async def _create_socket(self):
		# create a websocket and connect it to the endpoint.
		try:
			utils.logging('Create Socket.', self.merged_config)
			# needed when redirected for example
			if self.websocket is not None:
				await self.websocket.close()

			self.websocket = await websockets.client.connect(self.server_uri)
			# you may want to add additional connect parameters like 'ping_interval=xxx' and 'ping_timeout=xxx'
			# see the readme.md file for a possible reason
			utils.logging('Websocket is connected to: ' + self.server_uri, self.merged_config)
		except Exception as err:
			utils.logging('Websockets error: ' + str(self.server_uri), self.merged_config)
			utils.logging('Websockets error: ' + str(err) or 'Empty error string returned.', self.merged_config)
			raise

	async def _send_api_request(self, data, silent = False):
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
			utils.logging('WS Request: Connection closed unexpectedly.', self.merged_config)
			raise ConnectionError('Connection closed unexpectedly.')

		# for all undefined websocket exceptions
		except Exception as err:
			utils.logging('Undefined WS error requesting the solmate API: ' + str(err), self.merged_config)
			raise

		# return the response
		if 'data' in response:
			return response['data']

		# raise exceptions based on that there was a response but it has issues
		elif 'error' in response:
			# contains the original websocket error data
			err = 'Response: ' + str(response['error'])
			if not silent:
				utils.logging(str(err), self.merged_config)
			raise Exception(err)
		else:
			err = 'The response did not contain any useful data.'
			utils.logging(str(err), self.merged_config)
			raise Exception(err)

	def ws_request(self, route, data, silent = False):
		# send request for the given route without error handling
		try:
			response = utils.create_async_loop().run_until_complete(
				self._send_api_request(
					{'id': self.message_id, 'route': route, 'data': data}, silent
				)
			)
			return response

		except RuntimeError as err:
			# an asyncio event loop is thread-specific
			# if there is a thread error, access was out of the current thread!
			# with such an error, we safely restart the program
			utils.logging('Error: ' + str(err), self.merged_config)
			utils.restart_program(self.merged_config, 0, mqtt)

	def authenticate(self):
		# authenticate in the cloud or solmate with the given serial number, password and device id
		try:
			# get the serial number to use for authentication
			# either the normal sn or, if exists and not empty, the spare sn
			serial_number = self.merged_config['eet_spare_serial_number'] or self.merged_config['eet_serial_number']

			# get the response to the request of the login route with the login data
			# note to expect that the endpoint 'login' exists
			utils.logging('Authenticating.', self.merged_config)
			response = utils.create_async_loop().run_until_complete(self._send_api_request(
				{
					'id': self.message_id,
					'route': 'login',
					'data': {
						'serial_num': serial_number,
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
					response = utils.create_async_loop().run_until_complete(self._send_api_request(
						{
							'id': self.message_id,
							'route': 'authenticate',
							'data': {
								'serial_num': serial_number,
								'signature': signature,
								'device_id': self.merged_config['eet_device_id']
							}
						}
					))

					# handle load-balancer redirect, if there is one
					if 'redirect' in response and response['redirect'] is not None:
						redirect_uri = str(response['redirect'])
						utils.logging('Got redirected to: ' + redirect_uri, self.merged_config)
						self._redirected_server(redirect_uri)
						utils.create_async_loop().run_until_complete(self._create_socket())
					else:
						# when there is no redirect parameter, the socket is connected to the correct instance
						correct_server = True

				# return the authenticated connection
				utils.logging('Authentication to ' + serial_number + ' successful!', self.merged_config)
				return response

			# authentication failed
			# the reason may be bad credentials or a failure when redirecting
			raise
			utils.logging('Authentication to ' + serial_number + ' failed!', self.merged_config)

		except Exception:
			# return that authentication failed
			utils.logging('Authentication to ' + serial_number + ' failed!', self.merged_config)
			raise

	def check_route(self, route, data):
		# send request for the given route including error handling

		try:
			self.ws_request(route, data, silent = True)
			# return true if the route exists
			return True

		except:
			# return false if not
			return False

	def query_solmate(self, route, data, merged_config, mqtt = False):
		# send request for the given route including error handling

		try: 
			response = self.ws_request(route, data)
			# request was successful, reset counter
			self.count_before_restart = 0
			return response

		except ConnectionError:
			# if a connection error happened, restart the program after waiting the timer_conn_err time
			# note that a connection error can also occur when a required parameter is not sent
			# also see '_send_api_request()'
			utils.timer_wait(merged_config, 'timer_conn_err', True)
			utils.restart_program(self.merged_config, 0, mqtt)

		except Exception as err:
			# depending on other exceptions do

			if len(self.err_kwds & set(str(err).replace(',', '').replace("'", '').split())) == len(self.err_kwds):
				# inexistent route (NotImplemetedError)
				# check if both keywords exist in the error message
				# in case, stop script if the endpoint does not exists, continue makes no sense
				# logging of which inexistent route was already done in '_send_api_request'
				utils.logging('Exiting.', self.merged_config)
				sys.exit()

			if 'sent 1011 (unexpected error) keepalive ping timeout' in str(err):
				# the endpoint existed, but the response was malformed
				# the websocket keep alive ping/pong failed (see readme.md), restart program immediately
				utils.logging('Keep alive ping/pong failed.', self.merged_config)
				utils.restart_program(self.merged_config, 0, mqtt)

			self.count_before_restart += 1

			if self.count_before_restart == merged_config['timer_attempt_restart']:
				# only on _consecutive_ unidentified issues
				# if waiting the response time did not help, restart after the n-th try 
				utils.logging('Too many failed consecutive request attempts: ' + str(self.count_before_restart), self.merged_config)
				utils.restart_program(self.merged_config, self.count_before_restart, mqtt)

			utils.logging('An non breaking error happened, continuing.', self.merged_config)
			utils.logging('Error: ' + str(err), self.merged_config)
			# the false response tells the caller about the incident, it is handled there
			return False
