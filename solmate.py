#!/usr/bin/env python
import os
import sys
import solmate_main as sol_main
import solmate_utils as sol_utils

version = '6.3.0'

if __name__ == '__main__':
	try:
		sol_main.main(version)
	except KeyboardInterrupt:
		# avoid printing ^C on the console
		# \r = carriage return (octal 015)
		sol_utils.logging('\rMain: Interrupted by keyboard')
		try:
			# terminate script by Control-C, exit code = 130
			sys.exit(130)
		except SystemExit:
			os._exit(130)

