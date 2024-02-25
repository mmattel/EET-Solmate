import pkg_resources
import semver
import solmate_utils as utils
import sys

# https://stackoverflow.com/questions/31304041/how-to-retrieve-pip-requirements-freeze-within-python

def package_version(console_print):
    installed = {pkg.key: pkg.version for pkg in pkg_resources.working_set}

    # check that the package version of the paho-mqtt library is major version 2
	# because of breaking changes from 1 --> 2
    version = semver.Version.parse(installed['paho-mqtt'])
    if version.major != 2:
        utils.logging('The paho-mqtt client must be major version 2, check the requirements in README.md, exiting.', console_print)
        sys.exit()

# if required, add other package queries

