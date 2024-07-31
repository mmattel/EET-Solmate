# esham Configuration

As a starting point, make a copy of the `.env-sample` file and name it the following:

* For Plain Python installations name it `.env`
* For an Appdeamon installation name it `.env_0`

**NOTE**

* A commented value is like not setting it. A commented key or a key with no value is treated like not present.
* Any value set for a key makes the value a "valid" one.
* A value set with `''` (empty) is boolean False!
* If the key is set but has no value, it is treated as boolean False!
* Any string values for boolean like True/true and False/false are converted into their boolean equivalent.

## Required Configurations

All keys in the MANDATORY section need to be present and configured according your environment.
You can read the respective comments for their purpose.

If you are upgrading from a release earlier than version 6, you can now safely remove any optional keys
from your config file that were present from former releases - except you actively use them with
different settings.

Note regarding MQTT configuration when using the HAOS MQTT Broker addon:

* Use the HA IP address or domain name to access the MQTT Broker addon.
* Instead using your admin user, it is generally recommended to generate a "dummy" user with a password
which will never logon. Any user in HA is granted MQTT Broker access.

## Optional Configurations

These keys are optional and do not need to be present. They are, if not present, internally generated
including their defaults if any. If optional configuration keys are set, the overwrite generated ones.

The following optional key schemes are present:

* `eet_`\
  These keys extend the mandatory eet key scheme.
* `default_`\
  The Solmate has some setting defaults when using the webUI. These settings are reused and can be overwritten
  when adding the respective key to the config. Note that changing defaults is on your own responsibility.
* `general_`\
  Only needed for debugging and testing purposes. 
* `timer_`\
  All timer related config keys.
