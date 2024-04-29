import json
import sys
import time
import signal
import paho.mqtt.client as mqtt
import solmate_utils as utils
import solmate_ha_config as ha_config
from paho.mqtt.packettypes import PacketTypes

# 1.6.1 --> 2.0.0 https://eclipse.dev/paho/files/paho.mqtt.python/html/migrations.html
# we later can improve the <property> opject use when turning off mqttv3.x protocol use
# see: http://www.steves-internet-guide.com/python-mqtt-client-changes/

class solmate_mqtt():

	def __init__(self, merged_config, smws_conn, disabled_api, console_print):
		# initialize MQTT with parameters
		self.merged_config=merged_config
		self.smws_conn = smws_conn
		self.console_print = console_print
		self.disabled_api = disabled_api
		self.connect_ok = None
		self.signal_reason = 0
		self.eet_reboot_in_progress = False
		self.remember_info_response = None
		self.remember_get_boost_response = None
		self.real_names = None
		self.fake_names = None
		self.routes = None
		self.configs = None
		self.has_ha_config = False

		utils.logging('Initializing the MQTT class.', self.console_print)

		# get the merged config and use mqtt relevant settings
		self.mqtt_server = self.merged_config['mqtt_server']
		self.mqtt_port = int(self.merged_config['mqtt_port'])
		self.mqtt_username = self.merged_config['mqtt_username']
		self.mqtt_password = self.merged_config['mqtt_password']
		self.mqtt_client_id = self.merged_config['mqtt_client_id']
		self.mqtt_topic = self.merged_config['mqtt_topic']
		self.mqtt_prefix = self.merged_config['mqtt_prefix']
		self.mqtt_ha = self.merged_config['mqtt_ha']

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
		# initialize the MQTT client
		utils.logging('Initializing the MQTT client.', self.console_print)

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
		try:
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
		except Exception as err:
			self.connect_ok = False
			utils.logging('MQTT connection failed: ' + str(err), self.console_print)
			sys.exit()

		# any other connection issues in _on_connect
		while self.connect_ok == None:
			# wait until the connection is either established or failed (like user/pwd typo)
			time.sleep(1)

		if not self.connect_ok:
			return

		# update HA topics to initialise correctly
		utils.logging('Update MQTT topics for Homeassistant.', self.console_print)

		# update the home assistant auto config info
		# each item needs its own publish
		self.fake_names, self.real_names, self.routes, names, self.configs, config_topics = ha_config.construct_ha_config_message(self)

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
					#print(x)
					self.mqttclient.subscribe(
						command_topic,
						options = None,
						properties = None
					)

	def graceful_shutdown(self):
		# the 'will_set' is not sent on graceful shutdown by design
		# we need to wait until the message has been sent, else it will not appear in the broker
		if self.connect_ok:
			utils.logging('\rShutting down MQTT gracefully.', self.console_print)
			# there can be cases where the connection is already gone.
			try:
				publish_result = self.mqttclient.publish(
					self.mqtt_availability_topic,
					payload = 'offline',
					qos = self.mqtt_qos,
					retain = True,
					properties = None
				)
				publish_result.wait_for_publish() 
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
				# but NOT when triggerd from the solmate class during a restart, as a restart
				# is NOT a hard interrupt which is triggered via the solmate_class: 'query_solmate'.
				raise KeyboardInterrupt
			if self.signal_reason == 2:
				# the program was politely asked to terminate, we log and grant that request.
				utils.logging('\rTerminated on request.', self.console_print)
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
			utils.logging('MQTT is connected and running.', self.console_print)
			# we should always subscribe via on_connect callback to be sure
			# the subscriptions are persisted across reconnections like client.subscribe("$SYS/#")
			# technically it is not necessary that the topic is already available.
			# will also trigger on disconnect and reconnect
			self._do_mqtt_subscriptions()

		else:
			switcher = {
				1: 'incorrect protocol version',
				2: 'invalid client identifier',
				3: 'server unavailable',
				4: 'bad username or password',
				5: 'not authorised',
			}
			self.connect_ok = False
			utils.logging('MQTT connection refused - ' + switcher.get(rc, 'unknown response'), self.console_print)
			self.mqttclient.loop_stop()

	def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties = None):
		if reason_code != 0:
			# https://github.com/eclipse/paho.mqtt.python/blob/master/src/paho/mqtt/reasoncodes.py
			# https://github.com/eclipse/paho.mqtt.python/issues/827
			utils.logging('MQTT disconnected: ' 
				+ str(reason_code.getName())
				+ ', packet: '
				+ str(PacketTypes.Names[reason_code.packetType]),
				self.console_print)

	def _on_publish(self, client, userdata, message, reason_codes, properties = None):
		print(f'MQTT messages published: {message}')

	def _on_message(self, client, userdata, message):
		# triggered on published messages when subscribed
		# the payload is binary and must be decoded first
		# an empty string is hardcoded with two consecutive double quotes that needs to get removed
		value = str(message.payload.decode('utf-8').replace('""', ''))
		topic = message.topic

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
			# IMPORTANT: values are casted to integer defined by the routes
			# check results from the solmate API if a route has a string = special treatment

			write_dict = {}
			boost = False

			# 'set_boost_injection' needs special treatment, we need to send time and wattage together!
			if self.remember_get_boost_response:
				boost_dict = {}
				for i in range(0,len(self.routes)):
					if self.routes[i] and 'set_boost_injection' in self.routes[i]:
						boost_value = self.remember_get_boost_response[self.fake_names[i]]
						write_dict[self.real_names[i]] = boost_value
					boost = True

			# 'set_user_xxx' (injection) is fine, we can process normally one by another
			for i in range(0,len(self.fake_names)):
				if topic in self.configs[i]:
					#print(self.fake_names[i])
					#print(self.real_names[i])
					#print(self.routes[i])
					#print(self.configs[i])
					if boost:
						# we cant rely on 'set_boost_injection', only on boost
						write_dict.update({self.real_names[i]: int(value)})
						#print(self.routes[i], write_dict)
						utils.mqtt_queue.put((self.routes[i], write_dict))
					else:
						if not 'set_boost_injection' in self.routes[i]:
							write_dict = {}
							write_dict[self.real_names[i]] = int(value)
							#print(self.routes[i], write_dict)
							utils.mqtt_queue.put((self.routes[i], write_dict))
					break

	def _manage_reboot(self, message):
		# exit if:
		# - not connected to the local solmate or
		# - there is already a reboot in progress
		if (not self.disabled_api['local']) or self.eet_reboot_in_progress:
			return

		# we have subscribed to the topic but the message can be empty
		# this happens on initialisation of _on_message
		if message:
			self.eet_reboot_in_progress = True
			self.send_sensor_update_message(self.remember_info_response, 'info')
			# new queue element = (route, key, value)
			utils.mqtt_queue.put(('shutdown', {'shut_reboot': 'reboot'}))
			utils.logging('Initializing SolMate Reboot.', self.console_print)

	def send_sensor_update_message(self, response, endpoint):
		# send a mqtt update message, the format is fixed
		# remember some settings necessary for other tasks
		if endpoint == 'info':
			# add additional info that is not present in the original response
			# remember the response to update the last message when rebooting
			self.remember_info_response = response
			# fake a operating_state into the response if not present
			response['operating_state'] = 'rebooting' if self.eet_reboot_in_progress else 'online'
			# fake a connected_to into the response if not present
			response['connected_to'] = 'local' if self.disabled_api['local'] else 'server'

		if endpoint == 'get_boost':
			# remember the response to update the last message when rebooting
			self.remember_get_boost_response = response

		# note the endpoint: it MUST match one defined in 'ha_config.construct_ha_config_message'
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

	def set_operating_state_normal(self):
		# do the cleanup after successful rebooting
		utils.logging('SolMate has Rebooted.', self.console_print)
		utils.logging('Back to normal operation.', self.console_print)
		self._init_button_command_topic('reboot', '')
		self.eet_reboot_in_progress = False
		self.send_sensor_update_message(self.remember_info_response, 'info')

	def _construct_update_message(self, response):
		# construct an update message
		# note that whatever keys in the response are present, they are processed
		# we need to replace real keys from teh API with fake keys defined in the construct message
		final = json.dumps(response)
		#print(json.dumps(response, indent=4))
		return final
