# Preperation for HAOS

   * [Important Information](#important-information)
   * [Preparation](#preparation)
   * [First Test](#first-test)
   * [HA Stuff](#ha-stuff)
   * [Execution Delay](#execution-delay)
   * [Monitoring](#monitoring)
   * [Updating the Scripts](#updating-the-scripts)
   * [Terminate the Solmate Script](#terminate-the-solmate-script)
   * [Manually Starting the Startup Script](#manually-starting-the-startup-script)

## Important Information

* When running HAOS you **MUST** prepare the environment to autostart the solmate script. Note that this is a bit different than using a dockerized HA with full OS access or a separate host as HAOS does not have any systemd and shell scripts hard stop after 60 seconds. But creativity finds its way...

* If you have more than one Solmate, each solmate script with it's configuration must run in its own directory.

* If you run the Mosquitto Broker Addon, any user who is created in HA is granted to access the broker. If you do not want to use the credentials of the admin account for the use with the solmate config, you **MUST** configure a (_dummy_) user and password for the solmate config. If no user is defined in the solmate config or the user used does not exist in HA, you will get a `MQTT connection refused: Not authorized` response and the script will stop. For more information on the user, see\
`http://<your-HA>:8123/hassio/addon/core_mosquitto/documentation`

* For any _configuration_ changes like creating or editing `.env` or `configuration.yaml`, you can use the Homeassistant SSH Addon like the `Advanced SSH & Web Terminal`. 

### How It Works

In a nutshell, a HA shell command is defined pointing to a script that can be used for an automation triggered on
startup like a reboot. This script prepares the environment by adding a job to crontab and other stuff. It than
copies another script that gets executed by `crond` (as part of HA's busybox integration) which finally gets started.
crond is not killed by the shell command time limit (it is a OS service!) and is therefore usable starting
long running tasks. crontab and other stuff is hard reset by HA on upgrades/reboot and the script takes care not
writing double entries. After python is executed, crond is killed to guarantee a single run. The procedure recognizes
an already running solmate script and exits in case. Note that we never know if HA removes crond, but I doubt they
will do so.

### How to Get HAOS System Access

HAOS is a very fenced system. Any *usual* thing like easy setting up SSH access is not present. It is important to know,
that HAOS under the hood uses docker to run a supervised system. When you have access to the bash shell inside the
container, the system does not differ to a standard Linux installation running a dockerized HA - which is what we
are looking for.

* For the basic setup, you **MUST NOT USE** any Homeassistant SSH Addon like the `Advanced SSH & Web Terminal`
These addons have limited access and permissions. Any trial to use it for this purpose will simply fail.
* For the configuration, you **CAN** use these terminals after the basic setup has been made.

### Shell Types

There are several shells for different purposes available.
To not get confused, here is a description.

You recognize easily in which shell (level) you are, based on the shell prompt:

* In the HAOS command console it is: `ha`
* Outside the Docker container it is: `#` 
* In Docker, it is e.g.: `homeassistant` 

`ha` --> login --> `#` --> docker exec ... --> `homeassistant`\
`homeassistant` --> ctrl-d --> `#` --> ctrl-d --> `ha`

### Prepare Basic Setup

Except configuring the `.env` file, viewing logs as described below or doing any changes in `configuration.yaml`,
every step is part of the basic setup procedure which also includes upgrades of the solmate files on new releases.
 
There are two ways gaining HAOS system access, select the one that fits your needs/capabilities. Note that HAOS
uses an US keyboard layout. If you are not used to it, open an own browser tab that shows the
[US keyboard layout](https://en.wikipedia.org/wiki/British_and_American_keyboards).

* Using a monitor and keyboard if you have easy access to the hardware.
* Accessing it via full [SSH access](https://developers.home-assistant.io/docs/operating-system/debugging/).

After you have HAOS system access and your prompt shows `ha >`, you need to do these two steps:

* Login into HAOS via the command `login`.\
`ha` --> `#`
* Login into the container with: `docker exec -it homeassistant bash`\
`#` --> `homeassistant`

Now you are inside the running container where you will do the preperation described in the next step.

## Preparation

After you are in the containers bash, you **MUST** put the scripts into a subfolder in the `/config` directory like
`/config/shell/solmate`. The config directory in the container is the only directory that is not cleaned up on reboot
or HA update/upgrade.

* Similar to the [standard installation](./prep-standard.md):
  * Get all source files into `/config/shell` via git clone which is most easiest.
* Prepare the [Python virtual environment](https://docs.python.org/3/library/venv.html):
  * `cd /config/shell/solmate`
  * `python -m venv /config/shell/solmate`
  * `source /config/shell/solmate/bin/activate`  
  (this activates the venv for upcoming tasks)
* Check that all required modules are installed.\
  Run `python check_requirements.py` to see which are missing.\
  You may need to cycle thru until all requirements are satisified.
* Run the following command to UPDATE system packages:\
  `python -m pip install --upgrade pip setuptools`\
  If you do not run this command, depending on the Python version used, you may get an error about not being able to load a module.
* As a venv "freezes" the python and library versions used, you must take care manually to upgrade it when there
  are new versions avialable.
  * The good thing is, that venv setups are reboot pesistent - means on reboot, you do not need to manually
    reinstall libraries.
  * Library upgrades can be done in the usual way for venv environments, for python check the documentation.
* [Configure](script-components.md#solmate_envpy) the `.env` file.
* Check that the two scripts `crond-execute` and `crond-prepare` are executable.\
  Type: `ls -la`, the crond-xxxx scripts should be printed green (respectively marked executable).
  If not run: `chmod +x <script-name>`.

## First Test

If you have configured all from the above, run a test to see if the script starts without issues:

* Change into the solmate directory `cd /config/shell/solmate`
* Activate the virtual env with `source /config/shell/solmate/bin/activate`
* Run `python -u solmate.py`

If you get a list of actions printed on the command line ending with\
`Once a day queries called by scheduler.`\
you have successfully configured the solmate script.

Finally press `ctrl-c` to end the script. Do not omit this!!

## HA Stuff

* Create a [shell command](https://www.home-assistant.io/integrations/shell_command/) by adding an entry in
  `/config/configuration.yaml`.  
  The `crond-prepare` script is the hook that prepares the environment when called.
  ```
  shell_command:
    start_solmate: /config/shell/solmate/crond-prepare
  ```
  Reboot HA\
  **Mandatory**, else the shell command will not get recognized.

* Create an [automation](https://www.home-assistant.io/getting-started/automation/) by defining:
  * IF: `Home Assistant is started`
  * EXECUTE: `Call a service` ==> `start_solmate`

* You will now see your automation in the list.

* For testing, change to the HA development page to services and select `Shell Command: start_solmate`.

## Execution Delay

When `crond-prepare` gets started, it takes between 3 and 5 minutes that crond finally executes `crond-execute`.
This is normal and expected. If interested, you can monitor the progress with `tail -f crond.log` respectively `tail -f crontabs.log`. The files are created in the solmate directory.

## Monitoring

Do the following to monitor the startup procedure and running logs, in a terminal of HAOS. Note that logs can't
be added to the normal HA logs by design. Note that cron logs are deleted on startup = no history:

* Run the `ps` command.  
  Here you see which processes are running.
* `crontabs.log` should be always of zero size, if not, there was a startup error.
* `crond.log` reports how crond processes the crontab entries.
* `nohup.log` simulates the syslog. Here you find all the logs coming from solmate.py like:  
  ```
  Create Socket.
  Websocket is connected to: ws://sun2plug.mmhome.local.lan:9124/
  Authenticating.
  Authentication successful!
  SolMate is online.
  Initializing the MQTT class.
  Initializing the MQTT client.
  MQTT is connected and running.
  Update MQTT topics for Homeassistant.
  Once a day queries called by scheduler.
  ```
  If this file becomes too big (not likely but can happen on a long rung), it is safe to remove it when
  `solmate.py` is NOT running. It gets recreated on startup. New data is appended.

## Updating the Scripts

To update the scripts, follow the instructions in the update item in the [Standard Preparation](../docs/prep-standard.md#standard-preparation). To restart the script, you must first terminate the existing one, see section below. Then you can either manually start it, see below or trigger the script start via the HA automation.

## Terminate the Solmate Script
 
If you want to terminate the solmate script started via crond, do the following in a HAOS terminal:

* Run `ps` and remember the number at the beginning of the `python solmate.py` line.
* Type `kill -9 <number>` and the process gets killed.
* You can now manually rerun the shell integration from the HA developer screen.

## Manually Starting the Startup Script

If you need to test or want to start the script via the terminal - on your own risk - do:

* Check and adapt the `SCRIPT_DIR` location in `crond-execute`.
* `./crond-execute` from the location where the script is stored.

Alternatively you can run `./crond-prepare` if you want to include the test using crond execution.
