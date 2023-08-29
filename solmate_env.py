import os
import sys
from dotenv import dotenv_values

def process_env(smws):
	# get all environment variables as dictionary
	# https://pypi.org/project/python-dotenv/
	# file either predefined or as cmd line option. option ID starts with 2
	env_file = '.env'

	if len(sys.argv) > 1:
		# use an env file if given as argument
		if os.path.isfile(sys.argv[1]) == True:
			env_file = sys.argv[1]
			smws.logging('Using env file: ' + str(env_file))
		else:
			smws.logging('Envvar file: ' + str(sys.argv[1]) + ' as argument not found, exiting.', True)
			sys.exit()
	else:
		if os.path.exists(env_file):
			# no envvar file as argument, but an .env file is present in the same directory
			smws.logging('Using env file: ' + str(env_file))
		else:
			# log that envars are expected otherwise
			smws.logging('No \'.env\' file found, expecting envvars.', True)

	full_config = {
		**dotenv_values(env_file),  # load env variables from file, if exist
		**os.environ,               # override loaded values with environment variables if exists
	}

	# only get the xyz_ values from the full dict as it is
	mqtt_config = {k: v for k, v in full_config.items() if k.startswith('mqtt_')}
	solmate_config = {k: v for k, v in full_config.items() if k.startswith('eet_')}

	# the timer values are all converted to absolute integer
	timer_config = {k: abs(int(v.strip() or 0)) for k, v in full_config.items() if k.startswith('timer_')}

	#print(mqtt_config)
	#print(solmate_config)
	#print(timer_config)

	return mqtt_config, solmate_config, timer_config
