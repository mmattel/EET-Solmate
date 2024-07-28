import os
import sys
import subprocess
import solmate_utils as utils
from importlib import metadata
from contextlib import contextmanager

# derived from https://github.com/frier-sam/pypi_multi_versions
# by this we do not need to import a new module
# we also need to adapt the code a bit

def install_version(package_name, version, path, print_output = False):
	# Installs a specific version of a package into the specified directory.

	try:
		full_package_name = f"{package_name}=={version}"
		cmd = [sys.executable, '-m', 'pip', 'install', full_package_name, "--target={}".format(path)]
		target_path = os.path.join(path, package_name, version)
		if not os.path.exists(target_path):
			os.makedirs(target_path)
		output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
		if print_output:
			# print output is intended for debugging purposes only, therefore no utils.logging
			print(output.decode())
	except subprocess.CalledProcessError as err:
		utils.logging('Importmanager: Installation failed: ' + str(err))
	except Exception as err:
		utils.logging('Importmanager: An error occurred during installation: ' + str(err))

@contextmanager
def import_helper(package_name, version, path):
	# Context manager to temporarily add a package version to sys.path.

	package_path = os.path.abspath(os.path.join(path, package_name, version))
	if not os.path.exists(package_path):
		raise ImportError(f"Package path {package_path} does not exist. Install the package first.")

	original_sys_path = sys.path.copy()
	sys.path.insert(1, package_path)

	try:
		yield
	finally:
		sys.path = original_sys_path

def get_available_version(package, required_version = ''):
	# get the latest available version matchin a pattern that can be downloaded
	# no required version provided means that just get the highest available
	# note that the package not mandatory needs to have a semver compliant versioning!!
	# means that 2 or 2.0 or 2.0.0 are all valid !

	found = True
	search_string = 'Available versions: '
	number_positions = len(required_version.split("."))
	if required_version.endswith('.'):
		# a trailing dot does not count, substract quantity by one and remove the dot
		number_positions-= 1
		required_version = required_version[:-1]

	try:
		cmd = [sys.executable, '-m', 'pip', 'index', 'versions', package]
		output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()
		# get the line that matches the search string
		matched_line = [line for line in output.split('\n') if search_string in line]
		version_list = ''.join(map(str, matched_line)).removeprefix(search_string).split(',')
		version_list = [item.strip() for item in version_list]
		# we now have a sorted descending list, higher first
		version_list.sort(reverse = True)

		if len(required_version) > 0:
			# get the first matching version
			for x in version_list:
				found = _versiontuple(required_version) >= _versiontuple(x)[:number_positions]
				if found:
					break
			return x
		else:
			# return the first in the list (= highest from the query)
			return version_list[0]
	except Exception as err:
		raise
		print(str(err))
		sys.exit()

def get_installed_version(package, required_version = ''):
	# check if a package is installed in the OS matches a pattern
	# no required version provided means that that we only check if present
	# note that the package not mandatory needs to have a semver compliant versioning!!
	# means that 2 or 2.0 or 2.0.0 are all valid !

	# https://discuss.python.org/t/the-fastest-way-to-make-a-list-of-installed-packages/23175/4
	# note that due to a "bug" in the importlib version in python 3.9,
	# we cant list installed packages, we can only query them if known.

	found = True
	found_version = False
	number_positions = len(required_version.split("."))
	if required_version.endswith('.'):
		# a trailing dot does not count, substract quantity by one and remove the dot
		number_positions-= 1
		required_version = required_version[:-1]

	try:
		# get the version of the installed package requested
		# will either return the version or raises an error if the package is not installed
		found_version = str(metadata.version(package))
		if len(required_version) > 0:
			# a version parameter has been provided, if not we dont need to check
#			found = _versiontuple(required_version) >= _versiontuple(found_version)[:number_positions]
			found = _versiontuple(found_version)[:number_positions] == _versiontuple(required_version)

		if found:
			return found, found_version, ""
		else:
			# we found a version but it does not match the criteria
			message = package + ' ' + str(found_version) + ' found, must be version ' + required_version + '. Check the requirements in README.md, exiting.'
			return found, found_version, message
	except Exception as err:
		# the package was not found
		return False, found_version, 'Importmanager: Package: ' + package + ' not found'

def _versiontuple(v):
	return tuple(map(int, (v.split("."))))
