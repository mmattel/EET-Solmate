import os
import sys
import json
import solmate_utils as sol_utils
from dotenv import dotenv_values

def process_env(version, self):
	# get all environment variables as dictionary
	# https://pypi.org/project/python-dotenv/
	# file either predefined or as cmd line option. option ID starts with 2
	env_file = '.env'
	merged_config = {}
	ok = True

	# first add optional keys and their defaults to allow logging and other stuff
	merged_config = _add_optional_env(version, self)

	#print(merged_config)
	#print(json.dumps(merged_config, indent=2, sort_keys=True))

	if self is None:
		# type defaults to False like when using default install
		# this is the case when you call e.g. python solmate.py <env-file>
		if len(sys.argv) > 1:
			# use an env file if given as argument
			if os.path.isfile(sys.argv[1]) == True:
				env_file = sys.argv[1]
				message = 'Using env file: ' + str(env_file)
			else:
				ok = False
				message = 'Envvar file: ' + str(sys.argv[1]) + ' as argument not found, exiting.'
		else:
			# we excpect that the .env file is in THE SAME directory from which the script has been started!!
			# if you start it from another directory, you must provide it as argument
			if os.path.exists(env_file):
				# no envvar file as argument, but an .env file is present in the same directory
				message = 'Using env file: ' + str(env_file)
			else:
			# log that envvars are expected otherwise
				ok = False
				message = 'No \'.env\' file found, expecting envvars.'
	else:
		# type is set, currently only appdaemon is handled
		# we could query type for whom is calling if we need more
		env_file = merged_config['general_install_path'] + env_file + self.env_name_appendix
		if os.path.exists(env_file):
			# .env file is present in the directory
			message = 'Using env file: ' + str(env_file)
		else:
		# log that envvars are expected otherwise
			ok = False
			message = 'No \'.env\' file found, expecting envvars.'

	if not ok:
		sol_utils.merged_config = merged_config
		if not type:
			# standard termination
			sol_utils.logging(message)
			sys.exit()
		else:
			# appdaemon termination
			self.log(message)
			sys.exit()

	full_config = {
		**dotenv_values(env_file),	# load env variables from file, if exist
		**os.environ				# override loaded values with environment variables if exists
	}

	# get relevant key:values from the full config as it is BUT with keys in lower case
	# when using envvars from the OS, these are ALWAYS uppercase, we use lowercase
	# this is important when using a containerized setup and you hand over the config via envvars
	fcl =  {k.lower(): v for k, v in full_config.items()}

	# get the config values for mqtt
	mqtt_config = {k: v for k, v in fcl.items() if k.startswith('mqtt_')}

	# get the config values for the solmate
	solmate_config = {k: v for k, v in fcl.items() if k.startswith('eet_')}
		# timer values are all converted to an absolute integer
	timer_config = {k: abs(int(v.strip() or 0)) for k, v in fcl.items() if k.startswith('timer_')}

	# get the config values for general program configuration
	general_config = {k: v for k, v in fcl.items() if k.startswith('general_')}

	# get the defaults for entities that can be set
	default_config = {k: abs(int(v.strip() or 0)) for k, v in fcl.items() if k.startswith('default_')}

	#print(mqtt_config)
	#print(solmate_config)
	#print(timer_config)
	#print(general_config)
	#print(default_config)

	# update the config settings
	merged_config |= mqtt_config | solmate_config | timer_config | general_config | default_config

	# all keys that contain 'False' or 'false' (string) are set to False (boolean)
	# all keys that contain 'True' or 'true' (string) are set to True (boolean)
	for k, v in merged_config.items():
		#print(k, str(v).lower())
		x = str(v).lower()
		if (x == 'False') or (x == 'false'):
			merged_config[k] = False
		if (x == 'True') or (x == 'true'):
			merged_config[k] = True
		if not x:
			merged_config[k] = False

	if not merged_config['general_use_mqtt']:
		# if the use of mqtt is required
		if not mqtt_config:
			# but there is no mqtt config defined
			message = 'There is no MQTT configuration, exiting.'
			# set key to use 'sol_utils.logging' because merged_config has not been populated
			sol_utils.merged_config = merged_config
			sol_utils.logging(message)
			sys.exit()

	#print(merged_config)
	#print(json.dumps(merged_config, indent=2, sort_keys=True))
	#sys.exit()

	if not solmate_config:
		message = 'There is no Solmate configuration, exiting.'
		sol_utils.merged_config = merged_config
		sol_utils.logging(message)
		sys.exit()

	# hand over the final array to be globally available
	sol_utils.merged_config = merged_config

def _add_optional_env(version, self):
	# if the key does not exist, it is added with a default value.
	# note that strings and empty values must be embedded in ''.
	# numeric values casted into their corresponding type.
	# limits and ranges are respected and derived from the webUI.
	# a good tip for reverse engineering the webUI is to search for `setSomeValue`

	add_optional = {}
	max_wattage = 800		# EU max limit
	max_battery = 90		# 90%
	min_boost_time = 0		# 0s
	max_boost_time = 10800	# 3h
	boost_max_wattage = 500	# originally from the webUI, this is only 500

	# add the version to the merged config keys
	add_optional.setdefault('internal_esham_version', version)
	# add self from the class if set to access additional functionalities
	add_optional.setdefault('internal_access_self', self)

	# eet spare is new and defaults to empty
	add_optional.setdefault('eet_spare_serial_number', False)

	# general values are now autogenerated and defaulted, except if manually set
	add_optional.setdefault('general_print_response', False)
	add_optional.setdefault('general_use_mqtt', True)
	add_optional.setdefault('general_api_info', False)
	add_optional.setdefault('general_console_timestamp', False)

	# with appdaemon, dont print default to the console, except when manually defined
	if self is None:
		add_optional.setdefault('general_console_print', True)
	else:
		add_optional.setdefault('general_console_print', False)

	# internal only, define the minimum required paho-mqtt library version
	# atm, we have only major, but this may change if there are incompatibilities with a minor one
	# will match the highest available version according the given pattern like 2 or 2.x or 2.x.y
	add_optional.setdefault('general_paho_mqtt_version', '2')

	# internal only, define the location for custom special package installs
	add_optional.setdefault('general_install_folder', 'my_packages')

	# internal only, this is the path this script is located
	# ending with a slash for ease of extension
	add_optional.setdefault('general_install_path', os.path.join(os.path.dirname(os.path.abspath(__file__)), ''))

	# timer values are now autogenerated and defaulted, except if manually set
	# due to historical reasons, they are not in the 'default_' prefix
	add_optional.setdefault('timer_offline', 600)
	add_optional.setdefault('timer_conn_err', 10)
	add_optional.setdefault('timer_live', 30)
	add_optional.setdefault('timer_reboot', 180)
	add_optional.setdefault('timer_attempt_restart', 3)

	# add an internal only 1s value timer
	# not exposed to .env-sample
	add_optional.setdefault('timer_min', 1)

	# these are the currently known default values extracted from the webUI
	add_optional.setdefault('default_boost_set_time', 600)
	add_optional.setdefault('default_boost_injection_wattage', boost_max_wattage)
	#merged_config.setdefault('default_boost_remaining_time', 0)
	# note there is no explicit min wattage level therefore hardcoded to 0

	add_optional.setdefault('default_user_minimum_injection', 0)
	add_optional.setdefault('default_user_maximum_injection', max_wattage)
	add_optional.setdefault('default_user_minimum_battery_percentage', 0)
	# note the max battery level is hardcoded to 90 (90%, search for: a.minBatteryFormat)

	# add internal defaults to query limits
	# these defaults are not exposed in the .env-sample and intended for internal use only
	add_optional['default_max_wattage'] = max_wattage
	add_optional['default_max_battery'] = max_battery
	add_optional['default_min_boost_time'] = min_boost_time
	add_optional['default_max_boost_time'] = max_boost_time

	# cap values if the are out of range
	if _not_in_range(0, add_optional['default_user_minimum_injection'], max_wattage):
		add_optional['default_user_minimum_injection'] = 0

	if _not_in_range(0, add_optional['default_user_maximum_injection'], max_wattage):
		meradd_optionalged_config['default_user_maximum_injection'] = boost_max_wattage

	if _not_in_range(0, add_optional['default_user_minimum_injection'], add_optional['default_user_maximum_injection']):
		add_optional['default_user_minimum_injection'] = 0

	if _not_in_range(0, add_optional['default_boost_injection_wattage'], max_wattage):
		add_optional['default_boost_injection_wattage'] = boost_max_wattage

	test = add_optional['default_boost_set_time']
	if _not_in_range(min_boost_time, test, max_boost_time):
		add_optional['default_boost_set_time'] = min_boost_time if test < min_boost_time else max_boost_time

	if _not_in_range(0, add_optional['default_user_minimum_battery_percentage'], max_battery):
		add_optional['default_user_minimum_battery_percentage'] = max_battery

	return add_optional

def _not_in_range(min_v, test, max_v):
	#print((not min_v <= test <= max_v), test)
	return not (min_v <= test <= max_v)
