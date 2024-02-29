# Breaking Changes

* When upgrading from release 3.0 to 4.x, some important steps need to be performed in the given sequence:
  * Upgrade / download all files from the repo, there are NEW and changed ones!
  * There are new dependencies. Check with `check-requirememts.py` if all of them are satisfied.

* When upgrading from release 2.x to 3.0, some important steps need to be performed in the given sequence:
  * Upgrade / download all files from the repo, there are NEW and changed ones!
  * There are new dependencies. Check with `check-requirememts.py` if all of them are satisfied.
  * You MUST upgrade at least the `paho-mqtt` to version 2.x  
  The code checks if this version is installed and refuses to continue if not!

* When upgrading from release 1.x to 2.x some important steps need to be performed in the given sequence:
  * Upgrade / download all files from the repo, there are NEW ones!
  * There are new dependencies. Check with `check-requirememts.py` if all of them are satisfied.
  * As suggestion, take the new `.env-sample` file as base for your config.  
  There are new envvars. Configure all envvars according your environment / needs.
