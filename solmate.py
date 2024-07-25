#!/usr/bin/env python
import solmate_main.py as main

version = '6.3.0'

if __name__ == '__main__':
	try:
		main.main(version)
	except KeyboardInterrupt:
		# avoid printing ^C on the console
		# \r = carriage return (octal 015)
		utils.logging('\rMain: Interrupted by keyboard')
		try:
			# terminate script by Control-C, exit code = 130
			sys.exit(130)
		except SystemExit:
			os._exit(130)

