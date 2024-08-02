import solmate_main as sol_main
import solmate_utils as sol_utils

# for appdaemon, we need an own "container" that calls the main program and
# catches/logs errors

def main(self, env_name_appendix):
	try:
		self.env_name_appendix = env_name_appendix
		sol_main.main(self)

	except SystemExit:
		# catch system exit raised by 'sys.exit()'
		sol_utils.logging('Main: Terminated by the program')

		# also log to appdaemon
		self.log('Solmate App ending with: ' + env_name_appendix + ': Terminated by the program')

# maybe we want to add in the future something like:
#
#import multiprocessing
#for p in multiprocessing.active_children():
#	if p.name == "solmate_appdaemon"+env_name_appendix:
#		p.terminate()
