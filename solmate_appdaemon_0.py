import os
import hassapi as hass
import multiprocessing
import solmate_appdsolmate as sol_appd_solmate

# for multi solmate installations, make the strings unique like '_0' or ...
# --> it defines the env file like '.env_0' to use for this app and the program
# name to start. see the docs for more details.
# note that the names defined must consistently be used in appdaemons definition files
env_name_appendix = '_0'

class Solmate_0(hass.Hass):

	def initialize(self):
		# help identifying the thread created based on the filename which is unique
		sn = os.path.splitext(os.path.basename(__file__))[0]
		#self.log(sn)

		for p in multiprocessing.active_children():
			# check if this app is already running
			if sn in p.name:
				self.log(str(p.name) + ' is already running, skip starting')
				break
		else:
			# only start if not found active
			# note that after starting, appdaemon continues normal processing
			# other apps independent of this started program
			multiprocessing.Process(
					target=sol_appd_solmate.main,
					name=sn,
					args=(self, env_name_appendix, sn)
					).start()
