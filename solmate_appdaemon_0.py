import hassapi as hass
import os
import sys
import solmate_main as sol_main
import solmate_utils as sol_utils

version = '7.0.0'

class Solmate_0(hass.Hass):

	def initialize(self):
		# for multi solmate installations, make this string unique like '_0' or ...
		# it defines the env file to use for this app. see the docs for more details
		# the env file must then be named in the same pattern'.env_0'
		self.env_name_appendix = '_0'
		try:
			# for appdaemon we need an additional parameter
			# self: the class identifyer
			#       main as this parameter optional defaults to None
			sol_main.main(version, self)
		except SystemExit:
			# we need to catch system exit raised by 'sys.exit()'
			# if this is not catched, appdaemon will be shut down !!
			sol_utils.logging('Main: Terminated by the program')
