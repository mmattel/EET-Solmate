import semver
import solmate_utils as utils
import sys
from importlib import metadata

def package_version(console_print):
	# https://discuss.python.org/t/the-fastest-way-to-make-a-list-of-installed-packages/23175/4
	# note that due to a "bug" in the importlib version in python 3.9,
	# we cant list installed packages, we can only query them if known.

	# check that the package version of the paho-mqtt library is major version 2
	# because of breaking changes from 1 --> 2
	version = semver.Version.parse(metadata.version('paho-mqtt'))
	if version.major != 2:
		utils.logging('The paho-mqtt client must be major version 2, check the requirements in README.md, exiting.', console_print)
		sys.exit()

	# if required, add other package version queries
