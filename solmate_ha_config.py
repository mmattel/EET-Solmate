import json

# the ha config setup is quite big so it is defined in an own file making mqtt better readable.
# the init parameters from 'self' are handed over and used as 'c_s'

def construct_ha_config_message(c_s):

	# it is EXTREMELY important to have the correct component set so that HA does the correct thing
	#
	# <discovery_prefix>/<component>/[<node_id>/]<object_id>/config|availability|state
	# c_s.mqtt_config_topic + names[i] + '/config'
	# https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery
	# https://www.home-assistant.io/integrations/sensor.mqtt/
	# https://www.home-assistant.io/integrations/sensor/#device-class
	# https://developers.home-assistant.io/docs/core/entity/sensor/#available-state-classes
	# https://www.home-assistant.io/docs/configuration/customizing-devices/#icon

	names = ['']			# assembled as '/' + virtual_topic + fake_name
	fake_names = ['']		# the name used in the mqtt message
	real_names = ['']		# the name used for the solmate API to get/set values
							# real/fake names can be different !
							# for automatic status updates, names in different topics must be identical
							# some naming differences take place like for 'set_user_maximum_injection'
							# technically this mapping is only necessary for writable keys 
	route = ['']			# the route for writable entities, needed for the solmate API
	configs = ['']			# the assembled config for each entry
	config_topics = ['']	# the topic for HA auto-config

	# note that device_values must be populated
	device_values = {}
	device_values['identifiers'] = c_s.merged_config['mqtt_topic'] + '_' + c_s.merged_config['eet_serial_number'] # ['eet_solmate']
	device_values['name'] = c_s.merged_config['mqtt_topic'] #'SOLMATE'
	device_values['model'] = 'SOLMATE G'
	device_values['manufacturer'] = 'EET Energy'
	device_values['serial_number'] = c_s.merged_config['eet_serial_number']

	if c_s.merged_config['eet_spare_serial_number']:
		device_values['via_device'] = c_s.merged_config['eet_spare_serial_number']

	# virtual topics
	live = '/live'
	live_n = 'live_'
	info = '/info'
	info_n = 'info_'
	button = '/button'
	button_n = 'button_'
	get_injection ='/get_injection'
	get_injection_n = 'get_injection_'
	get_boost = '/get_boost'
	get_boost_n = 'get_boost_'
	set_boost = '/set_boost'
	set_boost_n = 'set_boost_'
	set_inject = '/set_inject'
	set_inject_n = 'set_inject_'
	dictionaries = {}

# route: 'live_values'
# collection of live data. queried in relative short intervals
	i = 0
	route[i] = False
	fake_names[i] = 'timestamp'
	real_names[i] = 'timestamp'
	name = live_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_sensor_config_topic
	dictionaries[name] = {
		'name': name,
		# give the entiy a better identifyable name for the UI (timestamp is multiple present)
		# dont use a timestamp class, we manually generate it and manually define the icon
		'state_topic': c_s.mqtt_sensor_topic + live,
		'value_template': '{{ (value_json.' + fake_names[i] + " | as_timestamp()) | timestamp_custom('%Y-%m-%d %H:%M:%S') }}",
		'availability_topic': c_s.mqtt_availability_topic,
		'unique_id': c_s.merged_config['eet_serial_number'] + '_' + name,
		'device': device_values,
		'icon': 'mdi:progress-clock',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = False
	fake_names[i] = 'pv_power'
	real_names[i] = 'pv_power'
	name = live_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_sensor_config_topic
	dictionaries[name] = {
		'name': name,
		'device_class': 'power',
		'state_topic': c_s.mqtt_sensor_topic + live,
		'value_template': '{{ (value_json.' + fake_names[i] + ' | float(0)) | round(1) }}',
		'unique_id': c_s.merged_config['eet_serial_number'] + '_' + name,
		'availability_topic': c_s.mqtt_availability_topic,
		'unit_of_measurement': 'W',
		'device': device_values,
		'icon': 'mdi:solar-power-variant-outline',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = False
	fake_names[i] = 'inject_power'
	real_names[i] = 'inject_power'
	name = live_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_sensor_config_topic
	dictionaries[name] = {
	'name': name,
	'device_class': 'power',
	'state_topic': c_s.mqtt_sensor_topic + live,
	'value_template': '{{ (value_json.' + fake_names[i] + ' | float(0)) | round(1) }}',
	'unique_id': c_s.merged_config['eet_serial_number'] + '_' + name,
	'availability_topic': c_s.mqtt_availability_topic,
	'unit_of_measurement': 'W',
	'device': device_values,
	'icon': 'mdi:transmission-tower-import',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = False
	fake_names[i] = 'battery_flow'
	real_names[i] = 'battery_flow'
	name = live_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_sensor_config_topic
	dictionaries[name] = {
		'name': name,
		'device_class': 'power',
		'state_topic': c_s.mqtt_sensor_topic + live,
		'value_template': '{{ (value_json.' + fake_names[i] + ' | float(0)) | round(1) }}',
		'unique_id':c_s.merged_config['eet_serial_number'] + '_' + name,
		'availability_topic': c_s.mqtt_availability_topic,
		'unit_of_measurement': 'W',
		'device': device_values,
		'icon': 'mdi:home-battery-outline',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = False
	fake_names[i] = 'battery_state'
	real_names[i] = 'battery_state'
	name = live_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_sensor_config_topic
	dictionaries[name] = {
		'name': name,
		'state_topic': c_s.mqtt_sensor_topic + live,
		'value_template': '{{ ((value_json.' + fake_names[i] + ' | float(0)) * 100) | round(1) }}',
		'unique_id': c_s.merged_config['eet_serial_number'] + '_' + name,
		'availability_topic': c_s.mqtt_availability_topic,
		'unit_of_measurement': '%',
		'device': device_values,
		'icon': 'mdi:battery-high',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

	i += 1
	route.append(1)
	names.append(1)
	route[i] = False
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	fake_names[i] = 'temperature'
	real_names[i] = 'temperature'
	name = live_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_sensor_config_topic
	dictionaries[name] = {
		'name': name,
		'device_class': 'temperature',
		'state_topic': c_s.mqtt_sensor_topic + live,
		'value_template': '{{ (value_json.' + fake_names[i] + ' | float(0)) | round(1) }}',
		'unique_id': c_s.merged_config['eet_serial_number'] + '_' + name,
		'availability_topic': c_s.mqtt_availability_topic,
		'unit_of_measurement': '°C',
		'device': device_values,
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = False
	fake_names[i] = 'mppOutI'
	real_names[i] = 'mppOutI'
	name = live_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_sensor_config_topic
	dictionaries[name] = {
		'name': name,
		'device_class': 'current',
		'state_topic': c_s.mqtt_sensor_topic + live,
		'value_template': '{{ (value_json.' + fake_names[i] + ' | float(0)) | round(2) }}',
		'unique_id': c_s.merged_config['eet_serial_number'] + '_' + name,
		'availability_topic': c_s.mqtt_availability_topic,
		'device': device_values,
		'unit_of_measurement': 'A',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

# route: 'get_solmate_info'
# collection of info data like SW version. queried like once a day 
	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = False
	fake_names[i] = 'version'
	real_names[i] = 'version'
	name = info_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_sensor_config_topic
	dictionaries[name] = {
		'name': name,
		# no device class here as it is a string
		'state_topic': c_s.mqtt_sensor_topic + info,
		'value_template': '{{ value_json.' + fake_names[i] + ' | version }}',
		'unique_id': c_s.merged_config['eet_serial_number'] + '_' + name,
		'availability_topic': c_s.mqtt_availability_topic,
		'device': device_values,
		'entity_category': 'diagnostic',
		'icon': 'mdi:text-box-outline',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = False
	fake_names[i] = 'ip'
	real_names[i] = 'ip'
	name = info_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_sensor_config_topic
	dictionaries[name] = {
		'name': name,
		# no device class here as it is a string
		'state_topic': c_s.mqtt_sensor_topic + info,
		'value_template': '{{ value_json.' + fake_names[i] + ' }}',
		'unique_id': c_s.merged_config['eet_serial_number'] + '_' + name,
		'availability_topic': c_s.mqtt_availability_topic,
		'device': device_values,
		'entity_category': 'diagnostic',
		'icon': 'mdi:ip-outline',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = False
	fake_names[i] = 'timestamp'
	real_names[i] = 'timestamp'
	name = info_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_sensor_config_topic
	dictionaries[name] = {
		'name': name,
		# give the entiy a better identifyable name for the UI (timestamp is multiple present)
		# dont use a timestamp class, we manually generate it and manually define the icon
		'state_topic': c_s.mqtt_sensor_topic + info,
		'value_template': '{{ (value_json.' + fake_names[i] + " | as_timestamp()) | timestamp_custom('%Y-%m-%d %H:%M:%S') }}",
		'availability_topic': c_s.mqtt_availability_topic,
		'unique_id': c_s.merged_config['eet_serial_number'] + '_' + name,
		'device': device_values,
		'entity_category': 'diagnostic',
		'icon': 'mdi:clock-time-ten',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = False
	fake_names[i] = 'operating_state'
	real_names[i] = 'operating_state'
	name = info_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_sensor_config_topic
	dictionaries[name] = {
		'name': name,
		# no device class here as it is a string
		'state_topic': c_s.mqtt_sensor_topic + info,
		'value_template': '{{ value_json.' + fake_names[i] + ' }}',
		'unique_id': c_s.merged_config['eet_serial_number'] + '_' + name,
		'availability_topic': c_s.mqtt_availability_topic,
		'device': device_values,
		'entity_category': 'diagnostic',
		'icon': 'mdi:power-settings',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = False
	fake_names[i] = 'connected_to'
	real_names[i] = 'connected_to'
	name = info_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_sensor_config_topic
	dictionaries[name] = {
		'name': name,
		# no device class here as it is a string
		'state_topic': c_s.mqtt_sensor_topic + info,
		'value_template': '{{ value_json.' + fake_names[i] + ' }}',
		'unique_id': c_s.merged_config['eet_serial_number'] + '_' + name,
		'availability_topic': c_s.mqtt_availability_topic,
		'device': device_values,
		'entity_category': 'diagnostic',
		'icon': 'mdi:lan-connect',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

# collection of system switches like reboot
# add all switches/buttons here to be part of the system hierarchy
	dynamic_topic = c_s.mqtt_availability_topic if c_s.api_available['shutdown'] else c_s.mqtt_never_available_topic
	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = False
	fake_names[i] = 'reboot'
	real_names[i] = 'reboot'
	name = button_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_button_config_topic
	dictionaries[name] = {
		'name': name,
		'command_topic': c_s.mqtt_button_topic + '/command/' + fake_names[i],
		'availability_topic': dynamic_topic,
		'unique_id': c_s.merged_config['eet_serial_number'] + '_' + name,
		'value_template': '{{ value_json.' + fake_names[i] + ' }}',
		'device': device_values,
		'entity_category': 'config',
		'device_class': 'restart',
		'payload_press': 'doit',
		'qos': c_s.mqtt_qos,
		'retain': False
	}
	configs[i] = json.dumps(dictionaries[name])

# route: 'get_injection_settings'
# collection of existing injection settings, queried in the same interval of live values
	dynamic_topic = c_s.mqtt_availability_topic if c_s.api_available['hasUserSettings'] else c_s.mqtt_never_available_topic
	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = False
	fake_names[i] = 'user_minimum_injection'
	real_names[i] = 'user_minimum_injection'
	name = get_injection_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_sensor_config_topic
	dictionaries[name] = {
		'name': name,
		'device_class': 'power',
		'state_topic': c_s.mqtt_sensor_topic + get_injection,
		'value_template': '{{ (value_json.' + fake_names[i] + ' | float(0)) | round(1) }}',
		'unique_id':c_s.merged_config['eet_serial_number'] + '_' + name,
		'availability_topic': dynamic_topic,
		'unit_of_measurement': 'W',
		'device': device_values,
		'icon': 'mdi:home-lightning-bolt-outline',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = False
	fake_names[i] = 'user_maximum_injection'
	real_names[i] = 'user_maximum_injection'
	name = get_injection_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_sensor_config_topic
	dictionaries[name] = {
		'name': name,
		'device_class': 'power',
		'state_topic': c_s.mqtt_sensor_topic + get_injection,
		'value_template': '{{ (value_json.' + fake_names[i] + ' | float(0)) | round(1) }}',
		'unique_id':c_s.merged_config['eet_serial_number'] + '_' + name,
		'availability_topic': dynamic_topic,
		'unit_of_measurement': 'W',
		'device': device_values,
		'icon': 'mdi:home-lightning-bolt',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = False
	fake_names[i] = 'user_minimum_battery_percentage'
	real_names[i] = 'user_minimum_battery_percentage'
	name = get_injection_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_sensor_config_topic
	dictionaries[name] = {
		'name': name,
		'state_topic': c_s.mqtt_sensor_topic + get_injection,
		'value_template': '{{ ((value_json.' + fake_names[i] + ' | float(0)) | round(1)) }}',
		'unique_id': c_s.merged_config['eet_serial_number'] + '_' + name,
		'availability_topic': dynamic_topic,
		'unit_of_measurement': '%',
		'device': device_values,
		'icon': 'mdi:battery-low',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

# route: 'get_boost_injection'
# collection of existing boost injection settings, queried in the same interval of live values 
	dynamic_topic = c_s.mqtt_availability_topic if c_s.api_available['sun2plugHasBoostInjection'] else c_s.mqtt_never_available_topic
	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = False
	fake_names[i] = 'set_time'
	real_names[i] = 'set_time'
	name = get_boost_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_sensor_config_topic
	dictionaries[name] = {
		'name': name,
		'state_topic': c_s.mqtt_sensor_topic + get_boost,
		'value_template': '{{ (value_json.' + fake_names[i] + ' | int(0)) }}',
		'availability_topic': dynamic_topic,
		'unit_of_measurement': 's',
		# the name used can be read and written, so we need to distinguish
		'unique_id':c_s.merged_config['eet_serial_number'] + '_read_' + name,
		'device': device_values,
		'icon': 'mdi:timer-play-outline',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = False
	fake_names[i] = 'set_wattage'
	real_names[i] = 'set_wattage'
	name = get_boost_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_sensor_config_topic
	dictionaries[name] = {
		'name': name,
		'device_class': 'power',
		'state_topic': c_s.mqtt_sensor_topic + get_boost,
		'value_template': '{{ (value_json.' + fake_names[i] + ' | float(0)) | round(1) }}',
		# the name used can be read and written, so we need to distinguish
		'unique_id':c_s.merged_config['eet_serial_number'] + '_read_' + name,
		'availability_topic': dynamic_topic,
		'unit_of_measurement': 'W',
		'device': device_values,
		'icon': 'mdi:home-lightning-bolt',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = False
	fake_names[i] = 'remaining_time'
	real_names[i] = 'remaining_time'
	name = get_boost_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_sensor_config_topic
	dictionaries[name] = {
		'name': name,
		'state_topic': c_s.mqtt_sensor_topic + get_boost,
		'value_template': '{{ value_json.' + fake_names[i] + ' | int(0) }}',
		'availability_topic': dynamic_topic,
		'unit_of_measurement': 's',
		'unique_id':c_s.merged_config['eet_serial_number'] + '_' + name,
		'device': device_values,
		'icon': 'mdi:av-timer',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = False
	fake_names[i] = 'actual_wattage'
	real_names[i] = 'actual_wattage'
	name = get_boost_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_sensor_config_topic
	dictionaries[name] = {
		'name': name,
		'device_class': 'power',
		'state_topic': c_s.mqtt_sensor_topic + get_boost,
		'value_template': '{{ (value_json.' + fake_names[i] + ' | float(0)) | round(1) }}',
		'unique_id':c_s.merged_config['eet_serial_number'] + '_' + name,
		'availability_topic': dynamic_topic,
		'unit_of_measurement': 'W',
		'device': device_values,
		'icon': 'mdi:transmission-tower-import',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

# collection of user definable values like min/maximum_injection and minimum_battery_percentage etc
# set boost
	dynamic_topic = c_s.mqtt_availability_topic if c_s.api_available['sun2plugHasBoostInjection'] else c_s.mqtt_never_available_topic
	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = 'set_boost_injection'
	fake_names[i] = 'set_wattage'
	real_names[i] = 'wattage'
	name = set_boost_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_number_config_topic
	dictionaries[name] = {
		'name': name,
		'entity_category': 'config',
		'max': c_s.merged_config['default_boost_injection_wattage'],
		'min': 0, # hardcoded, see note in solmate_env.py
		'step': 5,
		'mode': 'slider',
		'state_topic': c_s.mqtt_sensor_topic + get_boost,
		'device_class': 'power',
		'command_topic': c_s.mqtt_number_topic + '/' + fake_names[i],
		'value_template': '{{ value_json.' + fake_names[i] + ' | int(0) }}',
		'unique_id':c_s.merged_config['eet_serial_number'] + '_' + name,
		'availability_topic': dynamic_topic,
		'unit_of_measurement': 'W',
		'device': device_values,
		'icon': 'mdi:home-plus-outline',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = 'set_boost_injection'
	fake_names[i] = 'set_time'
	real_names[i] = 'time'
	name = set_boost_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_number_config_topic
	dictionaries[name] = {
		'name': name,
		'entity_category': 'config',
		'max': c_s.merged_config['default_max_boost_time'],
		'min': c_s.merged_config['default_min_boost_time'],
		'step': 60,
		'mode': 'slider',
		'state_topic': c_s.mqtt_sensor_topic + get_boost,
		'command_topic': c_s.mqtt_number_topic + '/' + fake_names[i],
		'value_template': '{{ value_json.' + fake_names[i] + ' | int(0) }}',
		'unique_id':c_s.merged_config['eet_serial_number'] + '_' + name,
		'availability_topic': dynamic_topic,
		'unit_of_measurement': 's',
		'device': device_values,
		'icon': 'mdi:home-clock-outline',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

# set inject
	dynamic_topic = c_s.mqtt_availability_topic if c_s.api_available['hasUserSettings'] else c_s.mqtt_never_available_topic
	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = 'set_user_minimum_injection'
	fake_names[i] = 'user_minimum_injection'
	real_names[i] = 'injection'
	name = set_inject_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_number_config_topic
	dictionaries[name] = {
		'name': name,
		'entity_category': 'config',
		'max': c_s.merged_config['default_user_maximum_injection'],
		'min': 0,
		'step': 5,
		'mode': 'slider',
		'state_topic': c_s.mqtt_sensor_topic + get_injection, 
		'device_class': 'power',
		'command_topic': c_s.mqtt_number_topic + '/' + fake_names[i],
		'value_template': '{{ value_json.' + fake_names[i] + ' | int(0) }}',
		'unique_id':c_s.merged_config['eet_serial_number'] + '_' + name,
		'availability_topic': dynamic_topic,
		'unit_of_measurement': 'W',
		'device': device_values,
		'icon': 'mdi:priority-low',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = 'set_user_maximum_injection'
	fake_names[i] = 'user_maximum_injection'
	real_names[i] = 'injection'
	name = set_inject_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_number_config_topic
	dictionaries[name] = {
		'name': name,
		'entity_category': 'config',
		'max': c_s.merged_config['default_user_maximum_injection'],
		'min': c_s.merged_config['default_user_minimum_injection'],
		'step': 5,
		'mode': 'slider',
		'state_topic': c_s.mqtt_sensor_topic + get_injection, 
		'device_class': 'power',
		'command_topic': c_s.mqtt_number_topic + '/' + fake_names[i],
		'value_template': '{{ value_json.' + fake_names[i] + ' | int(0) }}',
		'unique_id':c_s.merged_config['eet_serial_number'] + '_' + name,
		'availability_topic': dynamic_topic,
		'unit_of_measurement': 'W',
		'device': device_values,
		'icon': 'mdi:priority-high',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

	i += 1
	route.append(1)
	names.append(1)
	fake_names.append(1)
	real_names.append(1)
	configs.append(1)
	config_topics.append(1)
	route[i] = 'set_user_minimum_battery_percentage'
	fake_names[i] = 'user_minimum_battery_percentage'
	real_names[i] = 'battery_percentage'
	name = set_inject_n + fake_names[i]
	names[i] = '/' + name
	config_topics[i] = c_s.mqtt_number_config_topic
	dictionaries[name] = {
		'name': name,
		'entity_category': 'config',
		'max': c_s.merged_config['default_max_battery'], # hardcoded, see note in solmate_env.py
		'min': c_s.merged_config['default_user_minimum_battery_percentage'],
		'step': 5,
		'mode': 'slider',
		'state_topic': c_s.mqtt_sensor_topic + get_injection, 
		'command_topic': c_s.mqtt_number_topic + '/' + fake_names[i],
		'value_template': '{{ value_json.' + fake_names[i] + ' | int(0) }}',
		'unique_id':c_s.merged_config['eet_serial_number'] + '_' + name,
		'availability_topic': dynamic_topic,
		'unit_of_measurement': '%',
		'device': device_values,
		'icon': 'mdi:battery-low',
		'retain': True
	}
	configs[i] = json.dumps(dictionaries[name])

	# json_formatted_str = json.dumps(dictionaries[name], indent=2, ensure_ascii = False)
	# print(json_formatted_str)

	return fake_names, real_names, route, names, configs, config_topics
