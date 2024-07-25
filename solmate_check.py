import semver
from importlib import metadata

def package_version(package, required_version):
	# https://discuss.python.org/t/the-fastest-way-to-make-a-list-of-installed-packages/23175/4
	# note that due to a "bug" in the importlib version in python 3.9,
	# we cant list installed packages, we can only query them if known.

	found_version = semver.Version.parse(metadata.version(package))

	positions = required_version.split(".")
	message = package + ' ' + str(found_version) + ' found, must be version ' + required_version + '. Check the requirements in README.md, exiting.'

	if len(positions) >= 1:
		if found_version.major != int(positions[0]):
			return False, message

	if len(positions) >= 2:
		if found_version.minor != int(positions[1]):
			return False, message

	if len(positions) >= 3:
		if found_version.patch != int(positions[2]):
			return False, message

	return True, ""

