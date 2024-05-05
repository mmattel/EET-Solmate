import os
import sys
from dotenv import dotenv_values
import solmate_utils as utils

def process_env():
	# get all environment variables as dictionary
	# https://pypi.org/project/python-dotenv/
	# file either predefined or as cmd line option. option ID starts with 2
	env_file = '.env'

	if len(sys.argv) > 1:
		# use an env file if given as argument
		if os.path.isfile(sys.argv[1]) == True:
			env_file = sys.argv[1]
			utils.logging('Using env file: ' + str(env_file))
		else:
			utils.logging('Envvar file: ' + str(sys.argv[1]) + ' as argument not found, exiting.', True)
			sys.exit()
	else:
		# we excpect that the .env file is in THE SAME directory from which the script has been started!!
		# if you start it from another directory, you must provide it as argument
		if os.path.exists(env_file):
			# no envvar file as argument, but an .env file is present in the same directory
			utils.logging('Using env file: ' + str(env_file))
		else:
			# log that envars are expected otherwise
			utils.logging('No \'.env\' file found, expecting envvars.', True)

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

	#print(mqtt_config)
	#print(solmate_config)
	#print(timer_config)
	#print(general_config)

	# merge the configs
	merged_config = mqtt_config | solmate_config | timer_config | general_config

	return merged_config
