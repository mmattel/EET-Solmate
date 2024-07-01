import os
import sys
from dotenv import dotenv_values
import json
import solmate_utils as utils

def process_env():
	# get all environment variables as dictionary
	# https://pypi.org/project/python-dotenv/
	# file either predefined or as cmd line option. option ID starts with 2
	env_file = '.env'
	merged_config = {}
	merged_config['general_console_print'] = 'True'

	if len(sys.argv) > 1:
		# use an env file if given as argument
		if os.path.isfile(sys.argv[1]) == True:
			env_file = sys.argv[1]
			utils.logging('Using env file: ' + str(env_file), merged_config)
		else:
			utils.logging('Envvar file: ' + str(sys.argv[1]) + ' as argument not found, exiting.', merged_config)
			sys.exit()
	else:
		# we excpect that the .env file is in THE SAME directory from which the script has been started!!
		# if you start it from another directory, you must provide it as argument
		if os.path.exists(env_file):
			# no envvar file as argument, but an .env file is present in the same directory
			utils.logging('Using env file: ' + str(env_file), merged_config)
		else:
			# log that envvars are expected otherwise
			utils.logging('No \'.env\' file found, expecting envvars.', merged_config)

	# reset dictionary and do a full load from scratch
	merged_config = None
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

	# merge the configs
	merged_config = mqtt_config | solmate_config | timer_config | general_config | default_config

	# add optional keys and their defaults if available
	merged_config = _add_optional_env(merged_config)

	#print(json.dumps(merged_config, indent=2, sort_keys=True))
	#sys.exit()

	return merged_config

def _add_optional_env(merged_config):
	# if the key does not exist, it is added with a default value.
	# note that strings and empty values must be embedded in ''.
	# numeric values casted into their corresponding type.
	# limits and ranges are respected and derived from the webUI.
	# a good tip for reverse engineering teh webUI is to search for `setSomeValue`

	max_wattage = 800		# EU max limit
	max_battery = 90		# 90%
	min_boost_time = 0		# 0s
	max_boost_time = 10800	# 3h
	boost_max_wattage = 500	# originally from the webUI, this is only 500

	merged_config.setdefault('eet_spare_serial_number', '')
	merged_config.setdefault('general_add_log', 'False')
	merged_config.setdefault('general_print_response', 'False')
	merged_config.setdefault('general_console_print', 'True')
	merged_config.setdefault('general_use_mqtt', 'True')
	merged_config.setdefault('general_api_info', 'False')

	# these are the currently known default values extracted from the webUI
	merged_config.setdefault('default_boost_set_time', 600)
	merged_config.setdefault('default_boost_injection_wattage', boost_max_wattage)
	#merged_config.setdefault('default_boost_remaining_time', 0)
	# note there is no explicit min wattage level therefore hardcoded to 0

	merged_config.setdefault('default_user_minimum_injection', 0)
	merged_config.setdefault('default_user_maximum_injection', max_wattage)
	merged_config.setdefault('default_user_minimum_battery_percentage', 0)
	# note the max battery level is hardcoded to 90 (90%, search for: a.minBatteryFormat)

	# add internal defaults to query limits
	# these defaults are not exposed in the .env-sample and intended for internal use only
	merged_config['default_max_wattage'] = max_wattage
	merged_config['default_max_battery'] = max_battery
	merged_config['default_min_boost_time'] = min_boost_time
	merged_config['default_max_boost_time'] = max_boost_time

	# cap values if the are out of range
	if _not_in_range(0, merged_config['default_user_minimum_injection'], max_wattage):
		merged_config['default_user_minimum_injection'] = 0

	if _not_in_range(0, merged_config['default_user_maximum_injection'], max_wattage):
		merged_config['default_user_maximum_injection'] = boost_max_wattage

	if _not_in_range(0, merged_config['default_user_minimum_injection'], merged_config['default_user_maximum_injection']):
		merged_config['default_user_minimum_injection'] = 0

	if _not_in_range(0, merged_config['default_boost_injection_wattage'], max_wattage):
		merged_config['default_boost_injection_wattage'] = boost_max_wattage

	test = merged_config['default_boost_set_time']
	if _not_in_range(min_boost_time, test, max_boost_time):
		merged_config['default_boost_set_time'] = min_boost_time if test < min_boost_time else max_boost_time

	if _not_in_range(0, merged_config['default_user_minimum_battery_percentage'], max_battery):
		merged_config['default_user_minimum_battery_percentage'] = max_battery

	return merged_config

def _not_in_range(min_v, test, max_v):
	#print((not min_v <= test <= max_v), test)
	return not (min_v <= test <= max_v)
