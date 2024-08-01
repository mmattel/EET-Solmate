# Migration

This guide describes the migration of the `crond` based `esham` HA installation to Appdaemon.

In a nutshell, it is the reverse order of the installation described in
[Preperation for HAOS](./prep-ha.md) (deprecated). Just see the topics in that guide how to do that.

**Note**\
When upgrading from a release 5 or below to 7 or above, as stated in the [changelog](../changelog.md),
there is _one_ breaking change with regards to entity naming:

`Entities got new names --> BREAKING`

## Steps

1. Login into the homeassistant docker container 
2. Terminate the running Solmate instance
3. Note or remember the settings for `mqtt_` and `eet_` defined in the `.env` file located at
   `/config/shell/solmate`. You will need them when resetting up the new configuration. Only if you
	have changed other, now optional settings as described in the [configuration](./configuration.md)
	guide, note them too. See the `.env-samle` for defaults.
4. Inactivate the automation in HA that triggers the `start_solmate` script on HA reboot by commenting
   `start_solmate: /config/shell/solmate/crond-prepare` in `/config/configuration.yaml`.
5. HA should now show the Solmate entities as `unavailable`.
6. Install and configure [Appdaemon](./appdaemon.md)\
   If up and running, the Solmate entities are showing up again with values.
7. Delete the `solmate` directory in `/config/shell/` by issuing `rm -r /config/shell/solmate`.
8. Delete the commented automation step that triggered the `start_solmate` script.
9. Reboot HA to make the changes effective.
