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

	def __init__(self):
		self.server_uri = utils.merged_config['eet_server_uri']
		self.count_before_restart = 0
		self.message_id = 0
		self.websocket = None
		# set of mandatory keywords in the query response if the endpoint does not exist
		self.err_kwds = {'Response:', 'NotImplemetedError'}

		utils.logging('Initializing websocket connection.')
		self._create_websocket()

	def _redirected_server(self, uri):
		self.server_uri = uri

	def _create_websocket(self):
		# create and connect to websocket
		try:
			utils.create_async_loop().run_until_complete(self._create_socket())
		except Exception as err:
			# the reason for the exception has been logged already, just exit
			utils.logging('Websockets error: ' + str(self.server_uri))
			raise Exception('websocket', 'timer_offline')

	def _close_websocket(self):
		# needed for example when redirected
		if self.websocket is not None:
			self.websocket.close()

	async def _create_socket(self):
		# create a websocket and connect it to the endpoint.
		try:
			utils.logging('Create Socket.')
			if self.websocket is not None:
				await self.websocket.close()

			self.websocket = await websockets.client.connect(self.server_uri)
			# you may want to add additional connect parameters like 'ping_interval=xxx' and 'ping_timeout=xxx'
			# see the readme.md file for a possible reason
			utils.logging('Websocket is connected to: ' + self.server_uri)
		except Exception as err:
			utils.logging('Websockets error: ' + str(self.server_uri))
			utils.logging('Websockets error: ' + str(err) or 'Empty error string returned.')
			raise Exception('websocket', 'timer_offline')

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
			utils.logging('WS Request: Connection closed unexpectedly.')
			raise ConnectionError('Connection closed unexpectedly.')

		# for all undefined websocket exceptions
		except Exception as err:
			utils.logging('Undefined WS error requesting the solmate API: ' + str(err))
			raise

		# return the response
		if 'data' in response:
			return response['data']

		# raise exceptions based on that there was a response but it has issues
		elif 'error' in response:
			# contains the original websocket error data
			err = 'Response: ' + str(response['error'])
			if not silent:
				utils.logging(err)
			raise Exception(err)
		else:
			err = 'The response did not contain any useful data.'
			utils.logging(err)
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

		except Exception as err:
			# an asyncio event loop is thread-specific
			# if there is a thread error, access was out of the current thread!
			# with such an error, we safely reconnect
			#utils.logging('Error: ' + str(err))
			raise Exception('websocket', 'timer_conn_err')

	def authenticate(self):
		# authenticate in the cloud or local with the given serial number, password and device id

		try:
			# get the serial number to use for authentication
			# either the normal sn or, if exists and not empty, the spare sn
			serial_number = utils.merged_config['eet_spare_serial_number'] or utils.merged_config['eet_serial_number']

			# get the response to the request of the login route using login data
			# note to expect that the endpoint 'login' exists
			utils.logging('Authenticating.')
			response = utils.create_async_loop().run_until_complete(self._send_api_request(
				{
					'id': self.message_id,
					'route': 'login',
					'data': {
						'serial_num': serial_number,
						'user_password_hash': base64.encodebytes(hashlib.sha256(utils.merged_config['eet_password'].encode()).digest()).decode(),
						'device_id': utils.merged_config['eet_device_id']
					}
				}
			))
		except Exception as err:
			# return that authentication failed
			utils.logging('Authentication to ' + serial_number + ' failed!')
			utils.logging(str(err))
			raise Exception('websocket', 'timer_offline')

		try:
			# if login was successful, get the hash to use for authenticated requests
			# check if we are local or cloud which needs a redirected authentication
			if 'success' in response and response['success'] and 'signature' in response:
				# Get the signature for the session to be reused for the next step instead of the password
				signature = response['signature']

				# check if Server redirects to another instance
				# (on first connect, the connenction is established to a load-balancer when using the cloud)
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
								'device_id': utils.merged_config['eet_device_id']
							}
						}
					))

					# if there is a load-balancer handle a redirect
					if 'redirect' in response and response['redirect'] is not None:
						redirect_uri = str(response['redirect'])
						utils.logging('Got redirected to: ' + redirect_uri)
						self._redirected_server(redirect_uri)
						utils.create_async_loop().run_until_complete(self._create_socket())
					else:
						# when there is no redirect parameter, the socket is connected to the correct instance
						correct_server = True

				# return the authenticated connection
				utils.logging('Authentication to ' + serial_number + ' successful!')
				return response

		except Exception as err:
			# authentication failed
			# the reason may be bad credentials or a failure when redirecting
			utils.logging('Authentication to ' + serial_number + ' failed!')
			utils.logging(str(err))
			raise Exception('websocket', 'timer_offline')

	def check_route(self, route, data):
		# send request for the given route including error handling

		try:
			self.ws_request(route, data, silent = True)
			# return true if the route exists
			return True

		except:
			# return false if not
			return False

	def query_solmate(self, route, data):
		# send request for the given route including error handling

		try: 
			response = self.ws_request(route, data)
			# request was successful, reset counter
			self.count_before_restart = 0
			return response

		except ConnectionError:
			# if a connection error happened, reconnect after waiting timer_conn_err
			# note that a connection error can also occur when a required parameter is not sent
			# also see '_send_api_request()'
			raise Exception('websocket', 'timer_conn_err')

		except Exception as err:
			# depending on other exceptions do

			if len(self.err_kwds & set(str(err).replace(',', '').replace("'", '').split())) == len(self.err_kwds):
				# inexistent route (NotImplemetedError)
				# check if both keywords exist in the error message
				# in case, stop script if the endpoint does not exists, continue makes no sense
				# logging of which inexistent route was already done in '_send_api_request'
				utils.logging('Exiting.')
				sys.exit()

			if 'sent 1011' in str(err):
				# the full string is: 'sent 1011 (unexpected error) keepalive ping timeout'
				# the endpoint existed, but the response was malformed
				# the websocket keep alive ping/pong failed (see readme.md)
				# for an immediately restart we need to implement a new timer with value 0 (or 1)
				utils.logging('Keep alive ping/pong failed.')
				raise Exception('websocket', 'timer_min')

			self.count_before_restart += 1

			if self.count_before_restart == utils.merged_config['timer_attempt_restart']:
				# only on _consecutive_ unidentified issues
				# if waiting the response time did not help, restart after the n-th try 
				utils.logging('Too many failed consecutive connection attempts: ' + str(self.count_before_restart))
				raise Exception('websocket', 'timer_conn_err')

			utils.logging('A non breaking error happened, continuing.')
			#utils.logging('Error: ' + str(err))
			# the false response tells the caller about the incident, it is handled there
			return False
