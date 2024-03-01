# Preperation for HAOS

When running HAOS you **MUST** prepare the environment to autostart the solmate script. Note that this is a bit different than using a dockerized HA or separate install environment as HAOS does not have any systemd and shell scripts hard stop after 60 seconds. But creativity finds its way...

In a nutshell, a shell command is defined pointing to a script that can be used for an automation triggered on
startup like a reboot. This script prepares the environment by adding a job to crontab and other stuff. It than
copies another script that gets executed by `crond` (as part of HA's busybox integration) which finally gets started.
crond is not killed by the shell command time limit (it is a OS service!) and is therefore usable starting
long running tasks. crontab and other stuff is hard reset by HA on upgrades/reboot and the script takes care not
writing double entries. After python is executed, crond is killed to guarantee a single run. The procedure recognizes
an already running solmate script and exits in case. Note that we never know if HA removes crond, but I doubt they
do so.

### Preperation

* You **MUST** put the scripts into a subfolder in the `/config` directory like `/config/shell/solmate`.  
  The config directory is the only directory that is not cleaned up on reboot.
* To prepare the [Python virtual environment](https://docs.python.org/3/library/venv.html) type:
  * `cd /config/shell/solmate`
  * `python -m venv /config/shell/solmate`
  * `source /config/shell/solmate/bin/activate` (this activates the venv for upcoming tasks)
* Similar to the [standard installation](./prep-standard.md), do:
  * Get all source files into this directory.
  * Check that all required modules are installed.  
     Run `python check_reqirements.py` to see which are missing.  
     You may need to cycle thru until all requirements are satisified.
   * [Configure](#solmate_envpy) the `.env` file.
* As a venv "freezes" the python and library versions used, you must take care manually to upgrade it when there
  are new versions avialable.
  * The good thing is, that venv setups are reboot pesistent - means on reboot, you do not need to manually
    reinstall libraries.
  * Library upgrades can be done in the usual way for venv environments, for python check the documentation.
* Check that the two scripts `crond-execute` and `crond-prepare` are executable.  
  If not run: `chmod +x <script-name>`.

### HA Stuff

* Create a [shell command](https://www.home-assistant.io/integrations/shell_command/) by adding an entry in
  `/config/configuration.yaml`.  
  The `crond-prepare` script is the hook that prepares the environment when called.
  ```
  shell_command:
    start_solmate: /config/solmate/shell/crond-prepare
  ```
* Create an [automation](https://www.home-assistant.io/getting-started/automation/) by defining:
  * IF: `Home Assistant is started`
  * EXECUTE: `Call a service` ==> `start_solmate`
* You will now see your automation in the list.
* For testing, change to the HA development page to services and select `Shell Command: start_solmate`.

### Execution Delay

When `crond-prepare` gets started, it takes between 3 and 5 minutes that crond finally executes `crond-execute`.
This is normal and expected. If interested, you can monitor the progress with `tail -f crond.log`.

### Monitoring

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

### Terminate the Solmate Script
 
If you want to end the solmate script, do the following in a HAOS terminal:

* Run `ps` and remember the number at the beginning of the `python solmate.py` line.
* Type `kill -9 <number>` and the process gets killed.
* You can now manually rerun the shell integration from the HA developer screen.

### Manually Starting the Startup Script

If you need to test or want to start the script via the terminal - on your own risk - do:

* Check and adapt the `SCRIPT_DIR` location in `crond-execute`.
* `./crond-execute` from the location where the script is stored.
