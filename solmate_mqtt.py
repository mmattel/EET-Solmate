import json
import sys
import time
import signal
import paho.mqtt.client as mqtt

class solmate_mqtt():

	def __init__(self, mqtt_config, smws, console_print):
		# initialize MQTT with parameters
		self.mqtt_config=mqtt_config
		self.smws = smws
		self.connect_ok = None
		self.console_print = console_print
		self.signal_reason = 0

		self.smws.logging('Initializing the MQTT class.', self.console_print)

		# use either envvars or the .env file, envvars overwrite .env
		self.mqtt_server = mqtt_config['mqtt_server']
		self.mqtt_port = int(mqtt_config['mqtt_port'])
		self.mqtt_username = mqtt_config['mqtt_username']
		self.mqtt_password = mqtt_config['mqtt_password']
		self.mqtt_client_id = mqtt_config['mqtt_client_id']
		self.mqtt_topic = mqtt_config['mqtt_topic']
		self.mqtt_prefix = mqtt_config['mqtt_prefix']
		self.mqtt_ha = mqtt_config['mqtt_ha']

		# https://www.home-assistant.io/integrations/mqtt/#discovery-topic
		# <discovery_prefix>/<component>/[<node_id>/]<object_id>/config
		#	eet/solmate/sensor
		#	homeassistant/solmate/sensor/sensor_name/config
		#	eet/solmate/sensor/sensor_name/availability
	
		self.mqtt_state_topic = self.mqtt_prefix + '/sensor/' + self.mqtt_topic
		self.mqtt_config_topic = self.mqtt_ha + '/sensor/' + self.mqtt_topic
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
		self.smws.logging('Initializing the MQTT client.', self.console_print)

		self.mqttclient = mqtt.Client(client_id = self.mqtt_client_id, clean_session = True)
		self.mqttclient.on_connect = self.on_connect
		#self.mqttclient.on_disconnect = self.on_disconnect
		#self.mqttclient.on_publish = self.on_publish	  # uncomment for testing purposes
		#self.mqttclient.on_message = self.on_message	  # uncomment for testing purposes		
		self.mqttclient.username_pw_set(self.mqtt_username, self.mqtt_password)
		self.mqttclient.will_set(self.mqtt_availability_topic, payload = "offline", qos = 0, retain = True)

		# server/port issues are handled here
		try:
			self.mqttclient.connect(self.mqtt_server, port = self.mqtt_port, keepalive = 70)
			self.mqttclient.loop_start()
		except Exception as err:
			self.connect_ok = False
			self.smws.logging('MQTT connection failed: ' + str(err), self.console_print)
			sys.exit()

		# any other connection issues in on_connect
		while self.connect_ok == None:
			# wait until the connection is either established or failed (like user/pwd typo)
			time.sleep(1)

		if not self.connect_ok:
			return

		# update HA topics in initialisation
		self.smws.logging('Update MQTT topics for Homeassistant.', self.console_print)

		# update the home assistant auto config info
		# each item needs its own publish
		# name and config are arrays
		# name contains the name for the config which is the full json string defining the message
		names, configs = self.construct_ha_config_message()

		for i in range(0,len(names)):
			#print(names[i])
			#print(configs[i])
			self.mqttclient.publish(self.mqtt_config_topic + names[i] + '/config', payload = configs[i], qos = self.mqtt_qos, retain = True)

	def graceful_shutdown(self):
		# the 'will_set' is not sent on graceful shutdown by design
		# we need to wait until the message has been sent, else it will not appear in the broker
		if self.connect_ok:
			self.smws.logging('\rShutting down MQTT gracefully.', self.console_print)
			publish_result = self.mqttclient.publish(self.mqtt_availability_topic, payload = "offline", qos = self.mqtt_qos, retain = True)
			publish_result.wait_for_publish() 
			self.mqttclient.disconnect()
			self.mqttclient.loop_stop()
			self.connect_ok = False
			# self.signal_reason defaults to 0, means no signal was used
			# 1 ... sigint (ctrl-c)
			# 2 ... sigterm (sudo systemctl stop eet.solmate.service)
			if self.signal_reason == 1:
				# (re) raise the kbd interrupt to proper exit like via __main__
				# but NOT when triggerd from the solmate class during a restart, as a restart
				# is NOT a hard interrupt which is triggered via the solmate_class: 'query_solmate'.
				raise KeyboardInterrupt
			if self.signal_reason == 2:
				# the program was politely asked to terminate, we log and grant that request.
				self.smws.logging('\rTerminated on request.', self.console_print)
				sys.exit()

	def on_connect(self, client, userdata, flags, rc):
		# http://www.steves-internet-guide.com/mqtt-python-callbacks/
		# online/offline needs to be exactly written like that for proper recognition in HA
		if rc == 0:
			client.publish(self.mqtt_availability_topic, payload = "online", qos = self.mqtt_qos, retain = True)
			self.connect_ok = True
			self.smws.logging('MQTT is connected and running.', self.console_print)
		else:
			switcher = {
				1: "incorrect protocol version",
				2: "invalid client identifier",
				3: "server unavailable",
				4: "bad username or password",
				5: "not authorised",
			}
			self.connect_ok = False
			self.smws.logging("MQTT connection refused - " + switcher.get(rc, "unknown response"), self.console_print)
			self.mqttclient.loop_stop()

	def on_publish(self, client, userdata, message):
		print(f"MQTT messages published: {message}")

	def on_message(self, client, userdata, message):
		# triggered on published message on subscription
		print('MQTT retain: ' + str(message.retain))

	def send_update_message(self, response, endpoint):
		update = self.construct_update_message(response)
		# send a mqtt update message, the format is fixed
		self.mqttclient.publish(self.mqtt_state_topic + '/' + endpoint, payload = update, qos = self.mqtt_qos, retain = True)

	def construct_update_message(self, response):
		# construct an update message
		# note that whatever keys in the response are present, they are processed
		# all possible keys must be defined in 'construct_ha_config_message' upfront

		final = json.dumps(response)
		#print(json.dumps(response, indent=4))

		return final

	def construct_ha_config_message(self):

		# <discovery_prefix>/<component>/[<node_id>/]<object_id>/config|availability|state
		# self.mqtt_config_topic + names[i] + '/config'
		# https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery
		# https://www.home-assistant.io/integrations/sensor.mqtt/
		# https://www.home-assistant.io/integrations/sensor/#device-class
		# https://developers.home-assistant.io/docs/core/entity/sensor/#available-state-classes
		# https://www.home-assistant.io/docs/configuration/customizing-devices/#icon

		names = [''] * 10
		configs = [''] * 10

		# note that device_values must be populated
		device_values = {}
		device_values["identifiers"] = ["eet_solmate"]
		device_values["name"] = "SOLMATE"
		device_values["model"] = "SOLMATE G"
		device_values["manufacturer"] = "EET Energy"

		live = '/live'
		info = '/info'
		live_n = 'live_'
		info_n = 'info_'
		dictionaries = {}

		i = 0
		n = 'timestamp'
		name = live_n + n
		names[i] = '/' + name
		dictionaries[name] = {
			"name": n,
			"friendly_name": name,
			# give the entiy a better identifyable name for the UI (timestamp is multiple present)
			# dont use a timestamp class, we manually generate it and manually define the icon
			"state_topic": self.mqtt_state_topic + live,
			"value_template": "{{ value_json." + n + " | as_timestamp() | timestamp_custom('%Y-%m-%d %H:%M:%S') }}",
			"availability_topic": self.mqtt_availability_topic,
			"unique_id": self.mqtt_topic + "_sensor_" + name,
			"device": device_values,
			"icon": "mdi:progress-clock"
		}
		configs[i] = json.dumps(dictionaries[name])
		# json_formatted_str = json.dumps(dictionaries[name], indent=2, ensure_ascii = False)
		# print(json_formatted_str)

		i += 1
		n = 'pv_power'
		name = live_n + n
		names[i] = '/' + name
		dictionaries[name] = {
			"name": n,
			"device_class": "power",
			"state_topic": self.mqtt_state_topic + live,
			"value_template": "{{ value_json." + n + " | round(1) }}",
			"unique_id": self.mqtt_topic + "_sensor_" + name,
			"availability_topic": self.mqtt_availability_topic,
			"unit_of_measurement": "W",
			"device": device_values,
			"icon": "mdi:solar-power-variant-outline"
		}
		configs[i] = json.dumps(dictionaries[name])

		i += 1
		n = 'inject_power'
		name = live_n + n
		names[i] = '/' + name
		dictionaries[name] = {
			"name": n,
			"device_class": "power",
			"state_topic": self.mqtt_state_topic + live,
			"value_template": "{{ value_json." + n + " | round(1) }}",
			"unique_id": self.mqtt_topic + "_sensor_" + name,
			"availability_topic": self.mqtt_availability_topic,
			"unit_of_measurement": "W",
			"device": device_values,
			"icon": "mdi:transmission-tower-import"
		}
		configs[i] = json.dumps(dictionaries[name])

		i += 1
		n = 'battery_flow'
		name = live_n + n
		names[i] = '/' + name
		dictionaries[name] = {
			"name": n,
			"device_class": "power",
			"state_topic": self.mqtt_state_topic + live,
			"value_template": "{{ value_json." + n + " | round(1) }}",
			"unique_id":self. mqtt_topic + "_sensor_" + name,
			"availability_topic": self.mqtt_availability_topic,
			"unit_of_measurement": "W",
			"device": device_values,
			"icon": "mdi:home-battery-outline"
		}
		configs[i] = json.dumps(dictionaries[name])

		i += 1
		n = 'battery_state'
		name = live_n + n
		names[i] = '/' + name
		dictionaries[name] = {
			"name": n,
			"state_topic": self.mqtt_state_topic + live,
			"value_template": "{{ value_json." + n + " * 100" + " | round(1) }}",
			"unique_id": self.mqtt_topic + "_sensor_" + name,
			"availability_topic": self.mqtt_availability_topic,
			"unit_of_measurement": "%",
			"device": device_values,
			"icon": "mdi:battery-high"
		}
		configs[i] = json.dumps(dictionaries[name])

		i += 1
		n = 'temperature'
		name = live_n + n
		names[i] = '/' + name
		dictionaries[name] = {
			"name": n,
			"device_class": "temperature",
			"state_topic": self.mqtt_state_topic + live,
			"value_template": "{{ value_json." + n + " | round(1)}}",
			"unique_id": self.mqtt_topic + "_sensor_" + name,
			"availability_topic": self.mqtt_availability_topic,
			"unit_of_measurement": "°C",
			"device": device_values
		}
		configs[i] = json.dumps(dictionaries[name])

		i += 1
		n = 'mppOutI'
		name = live_n + n
		names[i] = '/' + name
		dictionaries[name] = {
			"name": n,
			"device_class": "current",
			"state_topic": self.mqtt_state_topic + live,
			"value_template": "{{ value_json." + n + " }}",
			"unique_id": self.mqtt_topic + "_sensor_" + name,
			"availability_topic": self.mqtt_availability_topic,
			"device": device_values,
			"unit_of_measurement": "A"
		}
		configs[i] = json.dumps(dictionaries[name])

		i += 1
		n = 'version'
		name = info_n + n
		names[i] = '/' + name
		dictionaries[name] = {
			"name": n,
			# no device class here as it is a string
			"state_topic": self.mqtt_state_topic + info,
			"value_template": "{{ value_json." + n + " | version }}",
			"unique_id": self.mqtt_topic + "_sensor_" + name,
			"availability_topic": self.mqtt_availability_topic,
			"device": device_values,
			"icon": "mdi:text-box-outline"
		}
		configs[i] = json.dumps(dictionaries[name])

		i += 1
		n= 'ip'
		name = info_n + n
		names[i] = '/' + name
		dictionaries[name] = {
			"name": n,
			# no device class here as it is a string
			"state_topic": self.mqtt_state_topic + info,
			"value_template": "{{ value_json." + n + " }}",
			"unique_id": self.mqtt_topic + "_sensor_" + name,
			"availability_topic": self.mqtt_availability_topic,
			"device": device_values,
			"icon": "mdi:ip-outline"
		}
		configs[i] = json.dumps(dictionaries[name])

		i += 1
		n = 'timestamp'
		name = info_n + n
		names[i] = '/' + name
		dictionaries[name] = {
			"name": n,
			"friendly_name": name,
			# give the entiy a better identifyable name for the UI (timestamp is multiple present)
			# dont use a timestamp class, we manually generate it and manually define the icon
			"state_topic": self.mqtt_state_topic + info,
			"value_template": "{{ value_json." + n + " | as_timestamp() | timestamp_custom('%Y-%m-%d %H:%M:%S') }}",
			"availability_topic": self.mqtt_availability_topic,
			"unique_id": self.mqtt_topic + "_sensor_" + name,
			"device": device_values,
			"icon": "mdi:clock-time-ten"
		}
		configs[i] = json.dumps(dictionaries[name])

		return names, configs
