import json
import os
import sys
import time
import signal
import solmate_ha_config as sol_ha_config
import solmate_utils as sol_utils

# following code is executed on module load
# to make the code running successfully, a "late" import is required to use utils/env

# the code is necessary to enable importing a library with a different version
# than the one that is installed in the OS and we cant update it

# in particular, check if the installed package of paho-mqtt is major version 2
# if this is not the case, we need to install/import a specific one

# 1.6.1 --> 2.x.y https://eclipse.dev/paho/files/paho.mqtt.python/html/migrations.html
# we can later improve the <property> opject use when turning off mqttv3.x protocol use
# see: http://www.steves-internet-guide.com/python-mqtt-client-changes/

# get the target/min version range for paho-mqtt
# atm, we have only major, but this may change if there are incompatibilities with a minor one
pattern = sol_utils.merged_config['general_paho_mqtt_version']

# location of the custom special installed package
path = sol_utils.merged_config['general_install_path'] + sol_utils.merged_config['general_install_folder']

# this is the name of the package when installed and you run pip list
query_name = 'paho-mqtt'

# this is the name of the package when you need to install it
install_name = 'paho-mqtt'

# this are the commands to do the imports
imports = ['import paho.mqtt.client as mqtt', 'from paho.mqtt.packettypes import PacketTypes']
# this are the alias name objetcs from the imports used by the module.
# note that they must match
# note that if no alias (as) is used, check the 'return_object' code to get it
# does not apply to 'from' as the name is defined
name_objects = ['mqtt', 'PacketTypes']

# dynamically import packages based on the requirements defined
return_object = sol_utils.dynamic_import(pattern, path, query_name, install_name, imports, name_objects)

# get the imported objects to use with this module
for x,y in zip(name_objects, return_object):
	globals()[x] = y


class solmate_mqtt():
	# handle mqtt

	def __init__(self, api_available):
		# initialize MQTT with parameters
		self.api_available = api_available
		self.connect_ok = None
		self.signal_reason = 0
		self.eet_reboot_in_progress = False
		self.remember_info_response = None
		self.remember_get_boost_response = None
		self.remember_get_injection_response = None
		self.real_names = None
		self.fake_names = None
		self.routes = None
		self.configs = None
		self.has_ha_config = False
		self.first_query_has_run = False

		sol_utils.logging('MQTT: Initializing the class')

		# get the merged config and use mqtt relevant settings
		self.mqtt_server = sol_utils.merged_config['mqtt_server']
		self.mqtt_port = int(sol_utils.merged_config['mqtt_port'])
		self.mqtt_username = sol_utils.merged_config['mqtt_username']
		self.mqtt_password = sol_utils.merged_config['mqtt_password']
		self.mqtt_client_id = sol_utils.merged_config['mqtt_client_id']
		self.mqtt_topic = sol_utils.merged_config['mqtt_topic']
		self.mqtt_prefix = sol_utils.merged_config['mqtt_prefix']
		self.mqtt_ha = sol_utils.merged_config['mqtt_ha']

		# https://www.home-assistant.io/integrations/mqtt/#discovery-topic
		# <discovery_prefix>/<component>/[<node_id>/]<object_id>/config
		#	eet/solmate/sensor
		#	homeassistant/solmate/sensor/sensor_name/config
		#	eet/solmate/sensor/sensor_name/availability
	
		self.mqtt_button_topic = self.mqtt_prefix + '/button/' + self.mqtt_topic
		self.mqtt_number_topic = self.mqtt_prefix + '/number/' + self.mqtt_topic
		self.mqtt_sensor_topic = self.mqtt_prefix + '/sensor/' + self.mqtt_topic

		self.mqtt_button_config_topic = self.mqtt_ha + '/button/' + self.mqtt_topic
		self.mqtt_number_config_topic = self.mqtt_ha + '/number/' + self.mqtt_topic
		self.mqtt_sensor_config_topic = self.mqtt_ha + '/sensor/' + self.mqtt_topic

		self.mqtt_availability_topic = self.mqtt_prefix + '/sensor/' + self.mqtt_topic + '/availability'
		self.mqtt_never_available_topic = self.mqtt_prefix + '/sensor/' + self.mqtt_topic + '/never_available'

		# MQTT qos values (http://www.steves-internet-guide.com/understanding-mqtt-qos-levels-part-1/)
		# QOS 0 – Once (not guaranteed)
		# QOS 1 – At Least Once (guaranteed)
		# QOS 2 – Only Once (guaranteed)
		self.mqtt_qos = 2

	def signal_handler_sigint(self, signum, frame):
		# catch sigint (ctrl-c) and process a graceful shutdown
		self.signal_reason = 1
		self.graceful_shutdown()

	def signal_handler_sigterm(self, signum, frame):
		# catch sigterm (like from systemd) and process a graceful shutdown
		self.signal_reason = 2
		self.graceful_shutdown()

	def init_mqtt_client(self):
		try:
			# initialize the MQTT client. to see if it was successful, you must go to _on_connect
			sol_utils.logging('MQTT: Initializing the client')

			# protocol versions available
			# MQTTv31  = 3
			# MQTTv311 = 4
			# MQTTv5   = 5

			self.mqttclient = mqtt.Client(
				mqtt.CallbackAPIVersion.VERSION2,
				protocol = mqtt.MQTTv5,
				client_id = self.mqtt_client_id
			)
			self.mqttclient.on_connect = self._on_connect
			self.mqttclient.on_disconnect = self._on_disconnect

			#self.mqttclient.on_publish = self._on_publish	  # uncomment for testing purposes
			self.mqttclient.on_message = self._on_message
			self.mqttclient.username_pw_set(
				self.mqtt_username,
				self.mqtt_password
			)
			self.mqttclient.will_set(
				self.mqtt_availability_topic,
				payload = 'offline',
				qos = 0,
				retain = True
			)

			# to make the code work with both MQTTv5 and MQTTv3.1.1 we need to set the properties object to None
			# server/port issues are handled here
			self.mqttclient.connect(
				self.mqtt_server,
				port = self.mqtt_port,
				# http://www.steves-internet-guide.com/mqtt-keep-alive-by-example/
				# no need to set this value with paho-mqtt
				# this avoids on the broker the following message pairs beling logged
				# "Client solmate_mqtt closed its connection.
				# "Client xyz closed its connection.
				#keepalive = 70,
				bind_address = '',
				bind_port = 0,
				clean_start = mqtt.MQTT_CLEAN_START_FIRST_ONLY,
				properties = None
			)
			self.mqttclient.loop_start()

			#sol_utils.logging('MQTT: Connection failed: ' + str(err))
			#sys.exit()

			# wait until on_connect returns a response
			while self.connect_ok == None:
				# wait until the connection is either established or failed (like user/pwd typo)
				time.sleep(1)

			if not self.connect_ok:
				# when we fail connecting during initialisation, we have an auth error
				sys.exit()

		except Exception as err:
			# print any error that has occured
			sol_utils.logging(str(err))
			raise Exception('mqtt', 'timer_offline')

		# update HA topics to initialise correctly
		sol_utils.logging('MQTT: Update topics for Homeassistant')

		# update the home assistant auto config info
		# each item needs its own publish
		self.fake_names, self.real_names, self.routes, names, self.configs, config_topics = sol_ha_config.construct_ha_config_message(self)

		for i in range(0,len(self.fake_names)):
			#print(self.fake_names[i])
			#print(self.real_names[i])
			#print(self.routes[i])
			#print(names[i])
			#print(self.configs[i])
			#print(config_topics[i])
			self.mqttclient.publish(
				config_topics[i] + names[i] + '/config',
				payload = self.configs[i],
				qos = self.mqtt_qos,
				retain = True,
				properties = None
			)

		self.has_ha_config = True
		# lets do a correct subscription with all available command topics
		self._do_mqtt_subscriptions()

		# init the button to make it show up
		self._init_button_command_topic('reboot', '')

	def _init_button_command_topic(self, command, payload):
		# update the system command topic
		#print(command)
		#print(payload)
		self.mqttclient.publish(
			self.mqtt_button_topic + '/command/' + command,
			payload = json.dumps(payload),
			qos = self.mqtt_qos,
			retain = True,
			properties = None
		)

	def _do_mqtt_subscriptions(self):
		# subscribe to command topics to recieve messages triggered by HA
		# like reboot or setting a value. the callback is _on_message.
		# only run when ha_config has run, values needed come from this initialisation
		# triggered by _on_connect and init_mqtt_client
		# on_connect will trigger before ha_config has run, we need to cover this 
		if self.has_ha_config == True:
			for i in range(0,len(self.fake_names)):
				if 'command_topic' in self.configs[i]:
					y = json.loads(self.configs[i])
					command_topic = y['command_topic']
					self.mqttclient.subscribe(
						command_topic,
						options = None,
						properties = None
					)

	def graceful_shutdown(self):
		# the 'will_set' is not sent on graceful shutdown by design
		# we need to wait until the message has been sent, else it will not appear in the broker
		if self.connect_ok:
			sol_utils.logging('MQTT: Shutting down gracefully')
			# there can be cases where the connection is already gone.
			try:
				publish_result = self.mqttclient.publish(
					self.mqtt_availability_topic,
					payload = 'offline',
					qos = self.mqtt_qos,
					retain = True,
					properties = None
				)
				# max wait 4 sec to get the message published.
				# there can be cases where this would run forever
				publish_result.wait_for_publish(4) 
				self.mqttclient.disconnect()
				self.mqttclient.loop_stop()
			except Exception:
				pass

			self.connect_ok = False
			# 0 ... self.signal_reason defaults to 0, means no signal was used
			# 1 ... sigint (ctrl-c)
			# 2 ... sigterm (sudo systemctl stop eet.solmate.service)
			if self.signal_reason == 1:
				# (re) raise the kbd interrupt to proper exit like via __main__
				raise KeyboardInterrupt
			if self.signal_reason == 2:
				# the program was politely asked to terminate, we log and grant that request.
				sol_utils.logging('MQTT: Terminated on external request')
				sys.exit()

	def _on_connect(self, client, userdata, flags, reason_code, properties = None):
		# http://www.steves-internet-guide.com/mqtt-python-callbacks/
		# online/offline needs to be exactly written like that for proper recognition in HA
		if reason_code == 0:
			client.publish(
				self.mqtt_availability_topic,
				payload = 'online',
				qos = self.mqtt_qos,
				retain = True
			)
			client.publish(
				self.mqtt_never_available_topic,
				payload = 'offline',
				qos = self.mqtt_qos,
				retain = True
			)
			self.connect_ok = True
			sol_utils.logging('MQTT: Connected and running.')
			# we should always subscribe via on_connect callback to be sure
			# the subscriptions are persisted across reconnections like client.subscribe("$SYS/#")
			# technically it is not necessary that the topic is already available.
			# will also trigger on disconnect and reconnect
			self._do_mqtt_subscriptions()

			if self.first_query_has_run:
				# there was a disconnect and we have info values that are remembered
				# now thre is was a reconnect, update the values for HA
				self.send_sensor_update_message(self.remember_info_response, 'info')
		else:
			sol_utils.logging('MQTT: Connection refused: ' + str(reason_code))
			self.mqttclient.loop_stop()
			if str(reason_code).lower().strip() == 'not authorized':
				# if we are not authorized, no need for graceful_shutdown
				# this is so critical that we exit immediately
				sol_utils.logging('MQTT: Login credentials mismatch. Hard exit.')
			self.connect_ok = False

	def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties = None):
		# if we have not been connected formerly, it makes no sense to tell that we are now disconnected
		if not self.connect_ok:
			return

		if reason_code != 0:
			# if it has been connected once sucessfully, it tries to reconnect automatically
			# means no manual reconnect/raise/try/error is necessary

			# https://github.com/eclipse/paho.mqtt.python/blob/master/src/paho/mqtt/reasoncodes.py
			# https://github.com/eclipse/paho.mqtt.python/issues/827
			sol_utils.logging('MQTT: Disconnected: '
				+ str(reason_code.getName())
				+ ', packet: '
				+ str(PacketTypes.Names[reason_code.packetType])
				)

	def _on_publish(self, client, userdata, message, reason_codes, properties = None):
		print(f'MQTT messages published: {message}')

	def _on_message(self, client, userdata, message):

		# do not process before a first query run and publishing the results to mqtt has run
		if not self.first_query_has_run:
			sol_utils.logging('MQTT: Write back from MQTT before first full query completed, skipping.')
			return

		# there can be the _very_ rare case that both:
		# 'remember_get_boost_response' and 'remember_get_injection_response'
		# can be empty though 'first_query_has_run' is true.
		# this would lead to a hard error: TypeError: 'NoneType' object is not subscriptable
		# when trying to access an element inside the variable.
		# for both cases, do not accept any mqtt backwrites until initialisation is complete
		if remember_get_boost_response == None:
			sol_utils.logging('MQTT: Boost response from Solmate not fully initialized, skipping write back.')
			return
		if remember_get_injection_response == None:
			sol_utils.logging('MQTT: Injection response from Solmate not fully initialized, skipping write back.')
			return

		# triggered on published messages when subscribed
		# the payload is binary and must be decoded first
		# an empty string is hardcoded with two consecutive double quotes that needs to get removed
		# note that the topic equals one of the command_topics from the solmate_ha_config.
		value = str(message.payload.decode('utf-8').replace('""', ''))
		topic = message.topic

		#print(message.topic)
		#print('MQTT retain: ' + str(message.retain))
		#print("message: ", message.topic + ': ' + value)

		if value:
			# only proceed if there is a value, empty is not valid
			# reboot needs special treatment
			if topic.endswith('command/reboot'):
				# if triggered, the value coming from HA is 'doit'
				self._manage_reboot(value)
				return

			# add the result to the queue, processed in solmate.py
			# IMPORTANT: values are casted if possible to integer
			# check results from the solmate API if a route has a string = special treatment

			write_dict = {}
			boost_dict = {}
			boost = False
			matches = ["set_wattage", "set_time"]

			# 'set_boost_injection' needs special treatment, we need to send time and wattage together!
			# we can only distinguish via the unique topic
			# get the former values where one will get updated in the next step
			if any(x in topic for x in matches):
				for i in range(0,len(self.routes)):
					# a route can have a real route or false meaning no route present
					if self.routes[i]:
					# loop thru all routes and check if we have 'set_boost_injection' route
						if 'set_boost_injection' in self.routes[i]:
							#print(i, self.routes[i], self.fake_names[i])
							write_dict[self.real_names[i]] = self.remember_get_boost_response[self.fake_names[i]]
							boost = True
					#print(write_dict)
			#sys.exit()

			# now process the changes normally
			for i in range(0,len(self.fake_names)):
				if topic in self.configs[i]:
					#print(self.fake_names[i])
					#print(self.real_names[i])
					#print(self.routes[i])
					#print(self.configs[i])
					if boost:
						# only if boost has formerly been identified
						# update the changed key in the dictionary (two items are present)
						write_dict[self.real_names[i]] = self._check_value(
							self.fake_names[i],
							self.remember_get_boost_response,
							self.configs[i],
							value, topic)
						#print(self.routes[i], write_dict)
						sol_utils.mqtt_queue.put((self.routes[i], write_dict))
					else:
					# all others can be processed normally
						write_dict[self.real_names[i]] = self._check_value(
							self.fake_names[i],
							self.remember_get_injection_response,
							self.configs[i],
							value,topic)
						#print(self.routes[i], write_dict)
						sol_utils.mqtt_queue.put((self.routes[i], write_dict))
					break

	def _check_value(self, key, remember, config, value, topic):
		# check if we can cast the given value to integer
		# this can cause problems if we try to send a string from
		# locale 1 and convert it to interger with locale 2
		# in addition we check if values are in range (same as we do in solmate_env)

		c = json.loads(config)
		name = c['name']
		min_v = c['min']
		max_v = c['max']
		former = remember[key]

		#print(remember)
		#print(config)

		try:
			# convert and check if the values are in range
			x = int(value)

			# first test, check if in range
			if self._not_in_range(min_v, x, max_v):
				sol_utils.logging("Key " + "'" + str(key) + "': " + str(x) + " value out of range, using last valid: " + str(former))
				return former

			# only if we have min/max injection
			matches = ['user_minimum_injection', 'user_maximum_injection']
			if any(z in topic for z in matches):

				min_e = remember['user_minimum_injection']
				max_e = remember['user_maximum_injection']

				# next test, check if x > max_existing, it must be lower
				if 'user_minimum_injection' in topic:
					if x > max_e:
						#print('min', x, max_e)
						sol_utils.logging("Key " + "'" + str(key) + "': " + str(x) + " value bigger than: " + str(max_e) + " using last valid: " + str(former))
						return former

				# next test, check if x < min_existing, it must be higher
				if 'user_maximum_injection' in topic:
					if x < min_e:
						#print('max', x, min_v)
						sol_utils.logging("Key " + "'" + str(key) + "': " + str(x) + " value lower than: " + str(min_e) + " using last valid: " + str(former))
						return former
			#print(x)
			return x

		except Exception as err:
			# because we must return a valid value, we use the last valid one
			# which is definitely in the remember dictionary
			# logging the issue with the fake name as this one is used in
			# HA + the error cause + the errored value + the former valid value used
			sol_utils.logging("Key " + "'" + str(key) + "': " + str(err) + " using last valid: " + str(former))
			return former

	def _not_in_range(self, min_v, test, max_v):
		#print((not min_v <= test <= max_v), test)
		return not (min_v <= test <= max_v)

	def _manage_reboot(self, message):
		# exit if:
		# - reboot is not available for the commection or
		# - there is already a reboot in progress
		if (not self.api_available['shutdown']) or self.eet_reboot_in_progress:
			return

		# we have subscribed to the topic but the message can be empty
		# this happens on initialisation of _on_message
		if message:
			self.eet_reboot_in_progress = True
			self.send_sensor_update_message(self.remember_info_response, 'info')
			# new queue element = (route, key, value)
			sol_utils.mqtt_queue.put(('shutdown', {'shut_reboot': 'reboot'}))
			sol_utils.logging('Initializing SolMate Reboot.')

	def send_sensor_update_message(self, response, endpoint):
		# after connecting and initializing, this is the only location where we expect an error
		# that leads to the need re-initializing mqtt
		try:
			# send a mqtt update message, the format is fixed
			# remember some settings necessary for other tasks
			if endpoint == 'info':
				# add additional info that is not present in the original response
				# remember the last response
				self.remember_info_response = response
				# fake a operating_state into the response if not present
				response['operating_state'] = 'rebooting' if self.eet_reboot_in_progress else 'online'
				# fake a connected_to into the response if not present
				response['connected_to'] = 'local' if self.api_available['local'] else 'cloud'
				# fake a esham sw version (this program) into the response, for sure not present
				response['esham_version'] = sol_utils.merged_config['internal_esham_version']

			if endpoint == 'get_boost':
				# remember the last response
				self.remember_get_boost_response = response

			if endpoint == 'get_injection':
				# remember the last response
				self.remember_get_injection_response = response

			# note the endpoint: it MUST match one defined in 'sol_ha_config.construct_ha_config_message'
			# the endpoint groups entities together so they can be updated at once
			# the sort order is not relevant
			update = self._construct_update_message(response)
			self.mqttclient.publish(
				self.mqtt_sensor_topic + '/' + endpoint,
				payload = update,
				qos = self.mqtt_qos,
				retain = True,
				properties = None
			)

			# we now have passed at minimum the first query/update run
			# this is necessary to populate the remember.xxx dictionaries
			#print('first query run')
			self.first_query_has_run = True
		except:
			self.graceful_shutdown()
			raise Exception('mqtt', 'timer_conn_err')

	def set_operating_state_normal(self):
		# do the cleanup after successful rebooting
		sol_utils.logging('SolMate has Rebooted.')
		sol_utils.logging('Back to normal operation.')
		self._init_button_command_topic('reboot', '')
		self.eet_reboot_in_progress = False
		self.send_sensor_update_message(self.remember_info_response, 'info')

	def _construct_update_message(self, response):
		# construct an update message
		# note that whatever keys in the response are present, they are processed
		# we need to replace real keys from the API with fake keys defined in the construct message
		final = json.dumps(response)
		#print(json.dumps(response, indent=4))
		return final
