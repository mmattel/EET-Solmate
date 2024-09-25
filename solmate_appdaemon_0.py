import os
import hassapi as hass
import multiprocessing
import solmate_appdmonitor as sol_appd_monitor
import solmate_appdsolmate as sol_appd_solmate

# for multi solmate installations, make the strings unique like '_0' or ...
# --> it defines the env file like '.env_0' to use for this app and the program
# name to start. see the docs for more details.
# note that the names defined must consistently be used in appdaemons definition files
env_name_appendix = '_0'

# Set this to false if you do not want to monitor this app via HA
monitor_app = True

# nothing to do, just a global envvar necessary for the code
# defined in initialize, also used in terminate that is called by AD, therefore global
sn = None

# automatically start the app if AD is starting.
# set to False if you do not want to autostart esham on AD reboot.
# this has currently NO effect if you run AD as container and you reboot HA,
# because of a bug in AD which triggers the terminate() call AFTER HA is up again.
# terminate should trigger when AD disconnects but sadly triggers after reconnect...
# in that case, you need to manually start esham via the switch in HA that is catched when
# monitor_app is set to True
autostart = True

class Solmate_0(hass.Hass):

	def initialize(self):
		global sn
		# help identifying the thread created based on the filename which is unique
		sn = os.path.splitext(os.path.basename(__file__))[0]
		#self.log(sn)

		self.log('AppDaemon: starting solmate_0')

		for p in multiprocessing.active_children():
			# check if this app is already running
			if sn in p.name:
				self.log('AppDaemon: ' + str(p.name) + ' is already running, skip starting')
				break
		else:
			# only start if not already started and autostart is set to true
			# note that after starting, appdaemon continues normal processing
			# other apps independent of this started program
			if autostart:
				multiprocessing.Process(
						target=sol_appd_solmate.main,
						name=sn,
						args=(self, env_name_appendix, sn)
						).start()

		# start monitoring if enabled
		if monitor_app:
			self.log('AppDaemon: Monitoring enabled for ' + sn)
			# sn is this script name and necessary for process management and entity naming
			# self.name is the name defined in apps.yaml and necessary for restarting
			sol_appd_monitor.start_monitoring(self, sn, self.name)

	def terminate(self):
		global sn

		# the termination function is called when appdaemon is terminated or restarted as final action
		# note that terminate is currently flaky, see the comment in autostart above
		if monitor_app:
			sol_appd_monitor.stop_monitoring(self, sn)
