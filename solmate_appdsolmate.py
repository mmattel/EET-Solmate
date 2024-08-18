import solmate_main as sol_main
import solmate_utils as sol_utils

# for appdaemon, we need an own "container" that calls the main program and
# catches/logs errors

def main(self, env_name_appendix, sn):
	try:
		self.env_name_appendix = env_name_appendix
		sol_main.main(self)

	except SystemExit as err:
		# catch system exit raised by 'sys.exit()'
		sol_utils.logging('Main: Terminated the program')
