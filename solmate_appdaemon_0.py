import os
import hassapi as hass
from multiprocessing import Process
import solmate_appdsolmate as sol_appd_solmate

# for multi solmate installations, make the strings unique like '_0' or ...
# it defines the env file like '.env_0' to use for this app and the program
# name to start. see the docs for more details.
# note that the names defined must consistently be used in appdaemons definition files
env_name_appendix = '_0'

class Solmate_0(hass.Hass):

	def initialize(self):
		# help identifying the thread created based on the filename (is unique)
		sn = os.path.splitext(os.path.basename(__file__))[0]
		#self.log(sn)

		# note that after starting, appdaemon continues normal processing
		# other apps independent of this started program
		Process(
				target=sol_appd_solmate.main,
				name=sn,
				args=(self, env_name_appendix)
				).start()
