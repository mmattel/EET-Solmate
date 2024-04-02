import json
import sys
import time
import signal
import paho.mqtt.client as mqtt
import solmate_utils as utils

# 1.6.1 --> 2.0.0 https://eclipse.dev/paho/files/paho.mqtt.python/html/migrations.html
# we later can improve the <property> opject use when turning off mqttv3.x protocol use
# see: http://www.steves-internet-guide.com/python-mqtt-client-changes/

class solmate_mqtt():

	def __init__(self, merged_config, smws_conn, local, console_print):
		# initialize MQTT with parameters
		self.merged_config=merged_config
		self.smws_conn = smws_conn
		self.local = local
		self.console_print = console_print
		self.connect_ok = None
		self.signal_reason = 0
		self.eet_reboot_in_progress = False
		self.remember_info_response = None

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
		self.mqtt_preset_topic = self.mqtt_prefix + '/preset/' + self.mqtt_topic
		self.mqtt_sensor_topic = self.mqtt_prefix + '/sensor/' + self.mqtt_topic
		self.mqtt_switch_topic = self.mqtt_prefix + '/switch/' + self.mqtt_topic
		self.mqtt_button_config_topic = self.mqtt_ha + '/button/' + self.mqtt_topic
		self.mqtt_preset_config_topic = self.mqtt_ha + '/preset/' + self.mqtt_topic
		self.mqtt_sensor_config_topic = self.mqtt_ha + '/sensor/' + self.mqtt_topic
		self.mqtt_switch_config_topic = self.mqtt_ha + '/switch/' + self.mqtt_topic
		self.mqtt_availability_topic = self.mqtt_prefix + '/sensor/' + self.mqtt_topic + '/availability'

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
		# catch sigterm (liek from systemd) and process a graceful shutdown
		self.signal_reason = 2
		self.graceful_shutdown()

	def init_mqtt_client(self):
		# initialize the MQTT client
		utils.logging('Initializing the MQTT client.', self.console_print)

		# protocol versions available
		# MQTTv31 = 3
		# MQTTv311 = 4
		# MQTTv5 = 5

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
		# name and config are arrays
		# name contains the name for the config which is the full json string defining the message
		names, configs, config_topics = self._construct_ha_config_message()

		for i in range(0,len(names)):
			#print(names[i])
			#print(configs[i])
			#print(config_topics[i])
			self.mqttclient.publish(
				config_topics[i] + names[i] + '/config',
				payload = configs[i],
				qos = self.mqtt_qos,
				retain = True,
				properties = None
			)

		# set the button to make it show up
		self._update_button_command_topic('reboot', '')

	def _do_mqtt_subscriptions(self):
		# subscribe to the system/button/command/topic to recieve messages triggered by HA
		# like reboot or shutdown. the callback is _on_message.
		self.mqttclient.subscribe(
			self.mqtt_button_topic + '/command/reboot',
			options = None,
			properties = None
		)

	def _update_button_command_topic(self, command, payload):
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

	def graceful_shutdown(self):
		# the 'will_set' is not sent on graceful shutdown by design
		# we need to wait until the message has been sent, else it will not appear in the broker
		if self.connect_ok:
			utils.logging('\rShutting down MQTT gracefully.', self.console_print)
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
		else:
			self.mqttclient.loop_stop()
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
			self.connect_ok = True
			utils.logging('MQTT is connected and running.', self.console_print)
			# we should always subscribe from on_connect callback to be sure
			# the subscription(s) are persisted across reconnections like client.subscribe("$SYS/#")
			# it is not necessary that the topic is already available.
			self._do_mqtt_subscriptions()
		else:
			self.connect_ok = False
			utils.logging('MQTT connection refused: ' + str(reason_code), self.console_print)
			self.graceful_shutdown()

	def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties = None):
		if reason_code != 0:
			# https://github.com/eclipse/paho.mqtt.python/blob/master/src/paho/mqtt/reasoncodes.py
			utils.logging('MQTT disconnected: ' + str(reason_code.getName()), self.console_print)

	def _on_publish(self, client, userdata, message, reason_codes, properties = None):
		print(f'MQTT messages published: {message}')

	def _on_message(self, client, userdata, message):
		# triggered on published messages when subscribed
		# we can add here any actions based on subscribed topics
		# atm, manage to reboot the solmate
		# 'shutdown' would be possible if a topic/subscription is created
		#print('MQTT retain: ' + str(message.retain))
		#print("message: ", message.topic + ': ' + str(message.payload.decode('utf-8')))
		if message.topic.endswith('command/reboot'):
			self._manage_reboot(str(message.payload.decode('utf-8')).strip('\"'))

	def _manage_reboot(self, message):
		# exit if:
		# - not connected to the local solmate or
		# - there is already a reboot in progress
		if (not self.local) or self.eet_reboot_in_progress:
			return

		if message:
			# we have subscribed to a topic but the message can be empty
			# this happens on initialisation of _on_message
			self.eet_reboot_in_progress = True
			self.send_sensor_update_message(self.remember_info_response, 'info')
			utils.mqueue.put('reboot')
			utils.logging('Initializing SolMate Reboot.', self.console_print)

	def send_sensor_update_message(self, response, endpoint):
		# only if it is the 'info' endpoint
		# add additional info that is not present in the original to the response
		if endpoint == 'info':
			# remember the response to update the last message when rebooting
			self.remember_info_response = response
			# fake a operating_state into the response if not present
			response['operating_state'] = 'rebooting' if self.eet_reboot_in_progress else 'online'
			# fake a connected_to into the response if not present
			response['connected_to'] = 'local' if self.local else 'server'

		update = self._construct_update_message(response)
		# send a mqtt update message, the format is fixed
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
		self._update_button_command_topic('reboot', '')
		self.eet_reboot_in_progress = False
		self.send_sensor_update_message(self.remember_info_response, 'info')

	def _construct_update_message(self, response):
		# construct an update message
		# note that whatever keys in the response are present, they are processed
		# all possible keys must be defined in '_construct_ha_config_message' upfront

		final = json.dumps(response)
		#print(json.dumps(response, indent=4))

		return final

	def _construct_ha_config_message(self):

		# it is EXTREMELY important to have the correct component set so that HA does the correct thing
		#
		# <discovery_prefix>/<component>/[<node_id>/]<object_id>/config|availability|state
		# self.mqtt_config_topic + names[i] + '/config'
		# https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery
		# https://www.home-assistant.io/integrations/sensor.mqtt/
		# https://www.home-assistant.io/integrations/sensor/#device-class
		# https://developers.home-assistant.io/docs/core/entity/sensor/#available-state-classes
		# https://www.home-assistant.io/docs/configuration/customizing-devices/#icon

		names = [''] * 13
		configs = [''] * 13
		config_topics = [''] * 13

		# note that device_values must be populated
		device_values = {}
		device_values['identifiers'] = ['eet_solmate']
		device_values['name'] = 'SOLMATE'
		device_values['model'] = 'SOLMATE G'
		device_values['manufacturer'] = 'EET Energy'

		live = '/live'
		live_n = 'live_'
		info = '/info'
		info_n = 'info_'
		button = '/button'
		button_n = 'button_'
		preset = '/preset'
		preset_n = 'preset_'
		switch = '/switch'
		switch_n = 'switch_'
		dictionaries = {}

		# collection of live data. queried in relative short intervals
		i = 0
		n = 'timestamp'
		name = live_n + n
		names[i] = '/' + name
		config_topics[i] = self.mqtt_sensor_config_topic
		dictionaries[name] = {
			'name': n,
			'friendly_name': name,
			# give the entiy a better identifyable name for the UI (timestamp is multiple present)
			# dont use a timestamp class, we manually generate it and manually define the icon
			'state_topic': self.mqtt_sensor_topic + live,
			'value_template': '{{ value_json.' + n + " | as_timestamp() | timestamp_custom('%Y-%m-%d %H:%M:%S') }}",
			'availability_topic': self.mqtt_availability_topic,
			'unique_id': self.mqtt_topic + '_sensor_' + name,
			'device': device_values,
			'icon': 'mdi:progress-clock',
			'retain': True
		}
		configs[i] = json.dumps(dictionaries[name])
		# json_formatted_str = json.dumps(dictionaries[name], indent=2, ensure_ascii = False)
		# print(json_formatted_str)

		i += 1
		n = 'pv_power'
		name = live_n + n
		names[i] = '/' + name
		config_topics[i] = self.mqtt_sensor_config_topic
		dictionaries[name] = {
			'name': n,
			'device_class': 'power',
			'state_topic': self.mqtt_sensor_topic + live,
			'value_template': '{{ (value_json.' + n + ' | float(0)) | round(1) }}',
			'unique_id': self.mqtt_topic + '_sensor_' + name,
			'availability_topic': self.mqtt_availability_topic,
			'unit_of_measurement': 'W',
			'device': device_values,
			'icon': 'mdi:solar-power-variant-outline',
			'retain': True
		}
		configs[i] = json.dumps(dictionaries[name])

		i += 1
		n = 'inject_power'
		name = live_n + n
		names[i] = '/' + name
		config_topics[i] = self.mqtt_sensor_config_topic
		dictionaries[name] = {
			'name': n,
			'device_class': 'power',
			'state_topic': self.mqtt_sensor_topic + live,
			'value_template': '{{ (value_json.' + n + ' | float(0)) | round(1) }}',
			'unique_id': self.mqtt_topic + '_sensor_' + name,
			'availability_topic': self.mqtt_availability_topic,
			'unit_of_measurement': 'W',
			'device': device_values,
			'icon': 'mdi:transmission-tower-import',
			'retain': True
		}
		configs[i] = json.dumps(dictionaries[name])

		i += 1
		n = 'battery_flow'
		name = live_n + n
		names[i] = '/' + name
		config_topics[i] = self.mqtt_sensor_config_topic
		dictionaries[name] = {
			'name': n,
			'device_class': 'power',
			'state_topic': self.mqtt_sensor_topic + live,
			'value_template': '{{ (value_json.' + n + ' | float(0)) | round(1) }}',
			'unique_id':self. mqtt_topic + '_sensor_' + name,
			'availability_topic': self.mqtt_availability_topic,
			'unit_of_measurement': 'W',
			'device': device_values,
			'icon': 'mdi:home-battery-outline',
			'retain': True
		}
		configs[i] = json.dumps(dictionaries[name])

		i += 1
		n = 'battery_state'
		name = live_n + n
		names[i] = '/' + name
		config_topics[i] = self.mqtt_sensor_config_topic
		dictionaries[name] = {
			'name': n,
			'state_topic': self.mqtt_sensor_topic + live,
			'value_template': '{{ (((value_json.' + n + ' | float(0)) * 100) | round(1)) }}',
			'unique_id': self.mqtt_topic + '_sensor_' + name,
			'availability_topic': self.mqtt_availability_topic,
			'unit_of_measurement': '%',
			'device': device_values,
			'icon': 'mdi:battery-high',
			'retain': True
		}
		configs[i] = json.dumps(dictionaries[name])

		i += 1
		n = 'temperature'
		name = live_n + n
		names[i] = '/' + name
		config_topics[i] = self.mqtt_sensor_config_topic
		dictionaries[name] = {
			'name': n,
			'device_class': 'temperature',
			'state_topic': self.mqtt_sensor_topic + live,
			'value_template': '{{ (value_json.' + n + ' | float(0)) | round(1) }}',
			'unique_id': self.mqtt_topic + '_sensor_' + name,
			'availability_topic': self.mqtt_availability_topic,
			'unit_of_measurement': '°C',
			'device': device_values,
			'retain': True
		}
		configs[i] = json.dumps(dictionaries[name])

		i += 1
		n = 'mppOutI'
		name = live_n + n
		names[i] = '/' + name
		config_topics[i] = self.mqtt_sensor_config_topic
		dictionaries[name] = {
			'name': n,
			'device_class': 'current',
			'state_topic': self.mqtt_sensor_topic + live,
			'value_template': '{{ (value_json.' + n + ' | float(0)) | round(2) }}',
			'unique_id': self.mqtt_topic + '_sensor_' + name,
			'availability_topic': self.mqtt_availability_topic,
			'device': device_values,
			'unit_of_measurement': 'A',
			'retain': True
		}
		configs[i] = json.dumps(dictionaries[name])

		# collection of info data like SW version. queried like once a day 
		i += 1
		n = 'version'
		name = info_n + n
		names[i] = '/' + name
		config_topics[i] = self.mqtt_sensor_config_topic
		dictionaries[name] = {
			'name': n,
			# no device class here as it is a string
			'state_topic': self.mqtt_sensor_topic + info,
			'value_template': '{{ value_json.' + n + ' | version }}',
			'unique_id': self.mqtt_topic + '_sensor_' + name,
			'availability_topic': self.mqtt_availability_topic,
			'device': device_values,
			'icon': 'mdi:text-box-outline',
			'retain': True
		}
		configs[i] = json.dumps(dictionaries[name])

		i += 1
		n= 'ip'
		name = info_n + n
		names[i] = '/' + name
		config_topics[i] = self.mqtt_sensor_config_topic
		dictionaries[name] = {
			'name': n,
			# no device class here as it is a string
			'state_topic': self.mqtt_sensor_topic + info,
			'value_template': '{{ value_json.' + n + ' }}',
			'unique_id': self.mqtt_topic + '_sensor_' + name,
			'availability_topic': self.mqtt_availability_topic,
			'device': device_values,
			'icon': 'mdi:ip-outline',
			'retain': True
		}
		configs[i] = json.dumps(dictionaries[name])

		i += 1
		n = 'timestamp'
		name = info_n + n
		names[i] = '/' + name
		config_topics[i] = self.mqtt_sensor_config_topic
		dictionaries[name] = {
			'name': n,
			'friendly_name': name,
			# give the entiy a better identifyable name for the UI (timestamp is multiple present)
			# dont use a timestamp class, we manually generate it and manually define the icon
			'state_topic': self.mqtt_sensor_topic + info,
			'value_template': '{{ value_json.' + n + " | as_timestamp() | timestamp_custom('%Y-%m-%d %H:%M:%S') }}",
			'availability_topic': self.mqtt_availability_topic,
			'unique_id': self.mqtt_topic + '_sensor_' + name,
			'device': device_values,
			'icon': 'mdi:clock-time-ten',
			'retain': True
		}
		configs[i] = json.dumps(dictionaries[name])

		i += 1
		n= 'operating_state'
		name = info_n + n
		names[i] = '/' + name
		config_topics[i] = self.mqtt_sensor_config_topic
		dictionaries[name] = {
			'name': n,
			# no device class here as it is a string
			'state_topic': self.mqtt_sensor_topic + info,
			'value_template': '{{ value_json.' + n + ' }}',
			'unique_id': self.mqtt_topic + '_sensor_' + name,
			'availability_topic': self.mqtt_availability_topic,
			'device': device_values,
			'icon': 'mdi:power-settings',
			'retain': True
		}
		configs[i] = json.dumps(dictionaries[name])

		i += 1
		n= 'connected_to'
		name = info_n + n
		names[i] = '/' + name
		config_topics[i] = self.mqtt_sensor_config_topic
		dictionaries[name] = {
			'name': n,
			# no device class here as it is a string
			'state_topic': self.mqtt_sensor_topic + info,
			'value_template': '{{ value_json.' + n + ' }}',
			'unique_id': self.mqtt_topic + '_sensor_' + name,
			'availability_topic': self.mqtt_availability_topic,
			'device': device_values,
			'icon': 'mdi:lan-connect',
			'retain': True
		}
		configs[i] = json.dumps(dictionaries[name])

		# collection of system switches like reboot
		# add all switches/buttons here to be part of the system hierarchy
		i += 1
		n = 'reboot'
		name = button_n + n
		names[i] = '/' + name
		config_topics[i] = self.mqtt_button_config_topic
		dictionaries[name] = {
			'name': n,
			'friendly_name': name,
			'command_topic': self.mqtt_button_topic + '/command/' + n,
			'availability_topic': self.mqtt_availability_topic,
			'unique_id': self.mqtt_topic + '_' + name,
			'value_template': '{{ value_json.' + n + ' }}',
			'device': device_values,
			'entity_category': 'config',
			'device_class': 'restart',
			'payload_press': 'doit',
			'qos': self.mqtt_qos,
			'retain': False
		}
		configs[i] = json.dumps(dictionaries[name])

		# collection of presets like min/maximum_injection and minimum_battery_percentage etc
		# add all presets here to be part of the system hierarchy
#		i += 1
#		n = 'user_minimum_injection'
#		name = preset_n + n
#		names[i] = '/' + name
#		config_topics[i] = self.mqtt_preset_config_topic
#		dictionaries[name] = {
#			'name': n,
#			# the range is between 0 and 800, need to check ho to limit
#			'value_template': '{{ (value_json.' + n + ' | int ) }}',
#			'unique_id': self.mqtt_topic + '_sensor_' + name,
#			'availability_topic': self.mqtt_availability_topic,
#			'unit_of_measurement': '%',
#			'device': device_values,
#			'icon': 'mdi:battery-high',
#			'retain': True
#
#			'friendly_name': name,
#			'command_topic': self.mqtt_preset_topic + '/preset/' + n,
#			'availability_topic': self.mqtt_availability_topic,
#			'unique_id': self.mqtt_topic + '_' + name,
#			'value_template': '{{ value_json.' + n + ' }}',
#			'device': device_values,
#			'entity_category': 'config',
#			'device_class': 'restart',
#			'payload_press': 'doit',
#			'qos': self.mqtt_qos,
#			'retain': False
#		}
#		configs[i] = json.dumps(dictionaries[name])

		return names, configs, config_topics
