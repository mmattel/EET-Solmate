# Script Configuration

This document describes the configuration of the Solmate to HA scripts.

As a starting point, make a copy of the `.env-sample` file, name it `.env` and adapt it accordingly.

If you have version 6 or up of "Solmate to HA" software running, you can safely remove any optional keys from
your config file that were present from former releases - except you actively use them.

## Required Configurations

All keys in the MANDATORY section need to be present and configured according your environment.
You can read the respective comments for their purpose. 

## Optional Configurations

These keys are optional and do not need to be present. They are, if not present, internally generated
including their defaults if any. If present, the overwrite the generated ones.

The following key schemes are present:

* `eet_`\
These keys extend the mandatory eet key scheme.
* `default_`\
The Solmate has some setting defaults when using the webUI. These settings are reused and can be overwritten
when adding the respective key to the config. Note that changing defaults is on your own responsibility.
* `general_`\
Only needed for debugging and testing purposes. 
