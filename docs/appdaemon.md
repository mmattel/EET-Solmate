# Install via Appdeamon

   * [Prerequisite](#prerequisite)
   * [Process Overview](#process-overview)
   * [Download the esham Code](#download-the-esham-code)
   * [Appdeamon Installation](#appdeamon-installation)
      * [Install Appdaemon as AddOn](#install-appdaemon-as-addon)
      * [Install Appdaemon as Container](#install-appdaemon-as-container)
   * [Configure Appdaemon](#configure-appdaemon)
   * [Configure esham](#configure-esham)
   * [Appdaemon Startup](#appdaemon-startup)
   * [Start and Stop the App via HA](#start-and-stop-the-app-via-ha)

## Prerequisite

As prerequisite to make `esham` an Appdaemon app, Appdeamon must be present. Depending on the [HA
installation](https://www.home-assistant.io/installation) this can either be done by loading Appdaemon
as HA AddOn (like when using a HA appliance or a full HAOS install) or by running Appdaemon as container
somewhere else connected to HA. Functionality wise and mostly also from the setup, there is no difference. 

If you already have Appdaemon running, you can use this installation.

There are some example files prepared in the `appdaemon_config` folder easing the installation and preparation
process. Have a look when referenced in the text. When installing as container, you can either use the
`docker-compose.yaml` or `docker-run.txt` files to derive from.

## Process Overview

1. Download the `esham` code
2. Install Appdeamon
3. Configure Appdaemon apps
5. Copy files to Appdaemon
6. Configure `esham`
7. Start Appdaemon

## Download the esham Code

Most easiest, use git for getting `esham`. For details see:
[Download and Update esham Using git](download-with-git.md).
The download will be saved on your local device is not the final target!

## Appdeamon Installation

Installing Appdaemon is only necessary if it is not already installed.

### Install Appdaemon as AddOn

If it is already installed, check the configuration list item below to add required packages.

1. Go to `Settings` → `Add-ons` → `Add-on Store`\
   Search for `Appdaemon` and install it.
2. In the `Info` tab, set `Watchdog` to `true`
3. Start Appdaemon and when it has started, stop it again.\
   This will make Appdaemon create the required directory structure.

There are multiple ways to upload necessary files to HAOS/Appdaemon. The most easiest way is to
use the `SAMBA` addon:

4. Go to `Settings` → `Add-ons` → `Add-on Store`\
   Search for `SAMBA` and install it. Dont forget to add a user/pwd in the `Configuration` tab.
5. When `samba` has started, connect from you local machine to HA using the defined user and
   password. The ways how to connect differs per OS used. Search in Google for how to do that.

Change into the local mounted Appdaemon config directory: 

7. First, change into directory `addon_configs` → `a0d7b954_appdaemon`\
  Note that the name may differ but it contains `_appdaemon`.
8. Note that compared to the container installation, the addon's internal folder is
   `/config` and not `/conf`! This is important for the configuration of Appdaemon.
9. Then, see the [Configure Appdaemon](#configure-appdaemon) section for further actions.

### Install Appdaemon as Container

1. Create a local directory that will be used as docker volume containing all Appdaemon data.
2. To install Appdaemon as container, use the `docker-compose.yaml` or `docker-run.txt` as reference
   and adapt the volume path accordingly. Note that compared to the addon, the containers
3. Start Appdaemon and when it has started, stop it again.\
   This will make Appdaemon create the required directory structure.

Change into the local mounted Appdaemon config directory: 

4. First, change into the _local_ directory you defined as volume for the config `<local config path>`.
5. Note that compared to the addon installation, the container internal folder is
   `/conf` and not `/config`! This is important for the configuration of Appdaemon.

Create a HA `Long-lived access token` to to authenticate Appdeamon in HA:

6. In HA, click on your user symbol which usually can be found on the bottom left.
7. Click the `Security` tab and at the bottom, create a new token. Note that you only see this
   token once.
8. Then, see the [Configure Appdaemon](#configure-appdaemon) section for further actions.

## Configure Appdaemon

### Install packages required by `esham`

* **For Addon Installations Only**
   1. In AD `Configuration` tab, in `Python packages`, add all packages that are **not** commented in
   `esham's` `requirements.txt` file and save the setting.
	2. Restart Appdaemon, loading of the required modules can be seen in the Appdaemon logs.

* **For Container Installations Only**
   1. Nothing special needs to be done, because Appdaemon recurively checks for existing `requirements.txt`
	files and installs the modules listed accordingly, also see
	[Runtime dependencies](https://appdaemon.readthedocs.io/en/latest/DOCKER_TUTORIAL.html#runtime-dependencies)
	and the setup steps below.

### Prepare AppDaemon

To prepare Appdaemon, check that is not running! When running Appdaemon as HA AddOn, HA must run.

For further reference, use the `esham` Appdaemon example files from the git download as base which can be
found in the `appdaemon_config` directory:

Open the mounted folder as decribed in the installation section above.

If you are using multiple Solmates, the following needs to be done per Solmate. Note that all Solmates
share the same Python code but each Solmate has it's own Appdaemon setting, configuration and startup file.

* **For Addon Installations Only**
   1. No need to adapt `secrets.yaml` if exists
   2. In `appdaemon.yaml` DO NOT change the `appdaemon.plugins.HASS` section!

* **For Container Installations Only**\
  Only if this is a new installation of Appdaemon, use the examples as reference
   1. Copy the `secrets.yaml` to the same location of `appdaemon.yaml`
   2. Replace in `secrets.yaml` → `<your-ha-token-here>` with the `Long-lived access token` created before.
   3. Adapt `appdaemon.yaml` by copying the sub keys `ha_url` and `token` from the example into
      the `appdaemon.plugins.HASS` section.
   4. Replace the URL in `ha_url` according how you access your HA (`URL:PORT`)
   5. If not exists, add the config in `hadashboard`. This is necessary to access Appdaemon's admin console
      to e.g. monitor logs.

**For Both Installation Types**
1. From the mounted folder, open `appdaemon.yaml`.
2. Optional:\
   In the `appdaemon:` section, add if not present the key/value pairs:
   - `production_mode: True`.\
   This entry can silence AD container log entries like
   `Excessive time spent in utility loop`.
   - `missing_app_warnings: 0`\
   This entry silences found files warnings where there is no related app defined.\

   See the
   [Appdaemon documentation](https://appdaemon.readthedocs.io/en/latest/CONFIGURE.html#appdaemon) for more
   details on the keys.
3. Add at the bottom from the example the `logs:` section.\
   Depending if you are using `Addon` or `Container`, comment/delete the respective `filename:` key.
   They are mutual exclusive!
4. Change into the `apps` folder.
5. Add to the existing `apps.yaml` file the content from the example. This is the file that defines
   which programs will be started.
6. Create a `solmate` folder and change into.
7. Copy from your cloned `esham` folder:
   - all `solmate*.py` files.
	- the `.env-sample`.
   - IMPORTANT: For container installation only, copy `requirements.txt`.

## Configure esham

In any case, read the [configuration](./configuration.md) guide!

If you already have an `.env` file from other installation options, you can use that one but it needs
renaming! Else follow the guide linked.

## Appdaemon Startup

If everything is setup, start Appdaemon and monitor the internal logs. This can be done either via
`docker logs -f <container>` or via the log tab in the HA Addaemon addon.

On successful startup, you can access the Appdaemon admin console via:
* `Appdaemon URL:5050` or
* `HA URL:5050`

Then go to section `Logs` and select `solmate_0.log`. 

Finally, check that HA shows in MQTT the new Solmate device.

## Start and Stop the App via HA

If you want to stop and start `esham` via a toggle switch entity in HA, you need to manually
create an entity in HA first, for details see below. If this is not done, nothing breaks...

With the ability to stop/start the `esham` instance via a HA entity, you can e.g. easily reconfigure
`esham` without bringing Appdaemon down first.

You can disable automatically starting the `esham` instance by adapting the `autostart` variable in the
`solmate_appdaemon_0` file to `False`.

You can generally disable toggle switch management by setting the `monitor_app` variable in the
`solmate_appdaemon_0` file to `False`. Consequently you can skip the following procedure.

Note that entity changes are only considered if Appdaemon is running!

Note that for technical reasons, if you shutdown Appdaemon, the entity defined will **NOT** show the
`off` but the last state of the app. This is out of my control and maybe fixed by Appdaemon once.

**Toggle Switch Setup**: \
To toggle switch `esham`, you just need to add an integration in HA manually. \
`Settings → Devices & Services → Helpers → Create Helper`. \
Select the "Toggle (Schalter)" helper (`input_boolean`) and name it: `solmate_appdaemon_0`.
The name is important and must match the name of the Python file. Use the respective name if you have
multiple Solmates. For the icon, select `mdi:script-text-play-outline` or any other icon you like.
When done, restart Appdaemon. You can now stop and restart `esham` via HA.
