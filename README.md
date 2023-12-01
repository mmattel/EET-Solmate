# EET-Solmate with HomeAssistant / MQTT

A Python script to read data from a EET SolMate and send it to a MQTT broker for the use with Homeassistant.

   * [General Info](#general-info)
   * [Upgrading - Breaking Change](#upgrading---breaking-change)
   * [Important Improvements](#important-improvements)
   * [Preperation and Quick Start](#preperation-and-quick-start)
   * [Script Components](#script-components)
      * [solmate.py](#solmatepy)
         * [Known Routes](#known-routes)
      * [solmate_websocket.py](#solmate_websocketpy)
      * [solmate_mqtt.py](#solmate_mqttpy)
      * [solmate_utils.py](#solmate_utilspy)
      * [solmate_env.py](#solmate_envpy)
         * [Necessary Data in the '.env' File](#necessary-data-in-the-env-file)
   * [Error Handling](#error-handling)
   * [Example Calls](#example-calls)
   * [Run as systemd Service (Linux Only)](#run-as-systemd-service-linux-only)
   * [Home Assistant](#home-assistant)
      * [MQTT Sensors](#mqtt-sensors)
      * [Energy Dashboard](#energy-dashboard)
      * [Template Sensors](#template-sensors)

## General Info

**IMPORTANT INFORMATION:**

* HA, MQTT and this set of Python scripts are independent units.  
  You need to have as prerequisite HA and MQTT successfully up and running.
  They can therefore run on separate hosts/containers and connect to each other as configured.

* You can't run this scripts as [HA Python Integration](https://www.home-assistant.io/integrations/python_script/).  
 This solution contains a set of single python files working together and not a single one required by HA.
 Doubting that making it a single script would work as the necessary error handling will in case restart
 the script which may negatively interfere with HA.

* You need per solmate installed, one instance of the script individually configured (if you have more than one).

* Stability  
  Compared to the [solmate SDK](https://github.com/eet-energy/solmate-sdk), the code provided has tons of [error handling](#error-handling) that will make the script run continuosly even if "strange" stuff occurs.

## Upgrading - Breaking Change

When upgrading from release 1.x to 2.x some important steps need to be performed in the given sequence:

1. Upgrade / download all files from the repo, there are NEW ones!

2. There are new dependencies. Check with `check-requirememts.py` if all of them are satisfied.

3. As suggestion, take the new `.env-sample` file as base for your config.  
There are new envvars. Configure all envvars according your environment / needs.

## Important Improvements

With version 2.x, the code has been refactored and contains the following major improvements:

1. You can now **reboot** your Solmate via HA / MQTT.  
   This is beneficial if the Solmate SW needs a restart and you do not want to get outside.
  Consider that this is only possible if you use the local connection,
  as the internet connection does not provide this API route.
  When using the internet connection, though pressing reboot in HA, no action takes place.  
  This can bee identified as no actions are logged.
2. Querying the Solmate is now generally much more stable.  
   The timer used between queries is now asynchron which does not longer block websocket communication.
3. You can now use the local connection as default instead using the internet version.  
   Formerly, the local connection was much less stable than the internet one.  
   Using local, you always have access to your Solmate as long there is power and you are more independent
   compared to external server availability.

## Preperation and Quick Start

* For ease of handling, clone this repo locally using [git clone](https://github.com/git-guides/git-clone) assuming you have installed git and know how to use it. This makes updating to a newer release more easy. As rule of thumb, use your home directory as target.

* Otherwise, manually copy the files to a location of your choice.  
  As rule of thumb, use a folder in your home directory as target.

* Check that all required modules are installed.  
  Run `python check_reqirements.py` to see which are missing.  
  You may need to cycle thru until all requirements are satisified.

* [Configure](#solmate_envpy) the `.env` file.
* Open two shells (assuming you are running a Linux derivate):
  * In the first shell run: `tail -f /var/log/syslog | grep solmate` to monitor logs. <br>
Alternatively set `console_print` in `solmate.py` temporarily to true in the script.
  * In the second shell start the script with `python solmate.py` from the installed location.
* You should now see the script running successfully.  
  If not check the configuration.
* Monitor MQTT posts, use [MQTT Explorer](https://github.com/mmattel/Raspberry-Pi-Setup/tree/main#steps) to do so.  
  The SolMate should show up as `eet/sensor/solmate` (or how you configured it).
* Check that HA shows in MQTT the new SOLMATE/EET device.

## Script Components

### solmate.py

This is the main program that imports all other components. It also has a proper CTRL-C and SIGTERM handling.

To parametrize, you either can use:

1. the predifined `.env` file, or
2. an own file `python solmate.py <your-env-file>`, or
3. when no envvar file is present, envvars defined via the OS or e.g. docker

There is a job scheduler for jobs (currently only the `get_solmate_info` is defined) that only needs
to run once a day. The responses change rarely, but can, like the solmates sw-version. The job is
forced to run at startup and then on the defined interval, currently once a day at 23:45.

On successful startup, the following messages are logged (exampe):

```
Initializing websocket connection.
Create Socket.
Websocket is connected to: ws://sun2plug.<your-local-domain>:9124/
Authenticating.
Authentication successful!
SolMate is online.
Initializing the MQTT class.
Initializing the MQTT client.
MQTT is connected and running.
Update MQTT topics for Homeassistant.
Once a day queries called by scheduler.
```

#### Known Routes

This is informational only and possibly not complete. All routes have as data {} (= no data) except where mentioned

1. `get_api_info`
2. `get_solmate_info`
3. `live_values`
4. `get_user_settings`
5. `get_grid_mode`
6. `get_injection_settings`  
  Note that you must provide proper data as attribute, see `get_api_info` output for more details.
7. `logs`  
  Note that you must provide proper data as attribute, see `get_api_info` output for more details.
9. `shutdown`  
  This route has a data attribute like `{'shut_reboot': 'reboot'}`
10. `set_system_time`  
  This route has a data attribute like `{datetime: n}` where  
  `const e = On()()`, `n = e.utc().format(t)` and `t = "YYYY-MM-DDTHH:mm:ss"` (using javascript as base)

### `solmate_websocket.py`

1. Initialize with `smws_conn = smws.connect_to_solmate(merged_config, console_print)`.
2. Authenticate with `response = smws_conn.authenticate()`  
  Note that envvar `eet_server_uri` must be mandatory present, all other stuff will return an auth error. 
3. This returns the connection as response
4. Then either run a plain request with:  
`smc_conn.ws_request(route, data)`  
or a request including proper error handling  
`smc_conn.query_solmate(route, value, merged_config, mqtt)`  
`merged_config` provides waiting times for the next action in case of coverable errors.

### `solmate_mqtt.py`

Without going into much details, to make EET Solmate auto discoverable for Home Assistant, the subroutine `construct_ha_config_message` is called. Do intensively testing when changing stuff here. I recommend using [mqtt Explorer](https://github.com/mmattel/Raspberry-Pi-Setup/tree/main#steps) to monitor the message flow.

### `solmate_utils.py`

Provides the following commonly used routines:

* Define the message queue to process recieved messages from MQTT topics.
* `logging`  
Prints the given message to the console and to syslog - which is useful when running as deamon.
* `timer_wait`  
Waits the given time and logs, in case enabled, that it is waiting for the particular time.
* `restart_program`  
When called, restarts the script like from cmd line. Necessary for unrecoverable errors.

### `solmate_env.py`

This reads config data from the `.env` file or a file defined as cmd line argument.
You can also use envvars instead. To force using envvars, no `.env` file must be present or defined
as option on startup.

#### Necessary Data in the '.env' File

As a starting point, make a copy of the `.env-sample` file, name it `.env` and adapt it accordingly.

Following parameters are intended either for development or testing but feel free to adapt them according your needs.

* Define `general_add_log` as required to add any log output for default timers when using loops.  
  Can be set to `False` when running as deamon like with systemd. Note that `live_values` do not need any waiting time to be logged...

* Define `general_print_response` to enable/disable console print of the response.  
  Helpful when testing.

* Define `general_console_print` to enable logging using console additionally, syslog is always used.

* Define `general_use_mqtt` to globally enable/disable mqtt, makes it easier for testing.

## Error Handling

Errors are handled on best effort and in **most cases** handed over to the caller to decide.

1. Authentication error: `solmate.py` --> `sys.exit()`
2. `query_solmate` --> `inexistent route` --> `solmate_websocket` --> `sys.exit()`
3. Missing or wrong `data` in request --> `query_solmate` --> `send_api_request` --> `ConnectionClosedOK` -->  
watch the log, it will continue after the waiting time. Can't be covered due to missing details in the response!
4. When the `response` returned `False` --> `query_solmate` --> continue but count the number of consecutive errors. Restart after `timer_attempt_restart` attempts.
5. Occasionally, you may see automatically program restarts due to a websocket error raised:
`sent 1011 (unexpected error) keepalive ping timeout; no close frame received`. See [What does ConnectionClosedError: sent 1011 (unexpected error)](https://websockets.readthedocs.io/en/stable/faq/common.html#what-does-connectionclosederror-sent-1011-unexpected-error-keepalive-ping-timeout-no-close-frame-received-mean) for details. The program covers the error and restarts completely.

For those who are interested in the details of `sent 1011`: Timing in websocket responses is critical,
even when using asynchronous timers. If the underlaying ping-pong gets out of sync, a 1011 may occur.

## Example Calls

These are examples if you want to adapt the code on your own.

```
	# example data when using the logs route
	logs_data = {"timeframes": [
						{
							"start": "2023-08-18T10:00:00",
							"end": "2023-08-18T23:59:59",
							"resolution": 4
						}
					]
				}

	# get a solmate logs, call eg. one a day
	# query_solmate(route, value, timer_config, mqtt)
	response = smc_conn.query_solmate('logs', logs_data, timer_config, mqtt)
	if response != False:
		if not 'timestamp' in response:
			# fake a timestamp into the response if not present
			response['timestamp'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
		# add mqtt or other stuff here
		if printing:
			print_request_response('logs', response)
```

```
	# get the solmate info, as often you call the block
	# query_solmate(route, value, timer_config, mqtt)
	response = smc_conn.query_solmate(route, data, timer_config, mqtt)
	if response != False:
		if not 'timestamp' in response:
			# fake a timestamp into the response if not present
			response['timestamp'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
		# add mqtt or other stuff here
		if printing:
			print_request_response(route, response)
```

```
	# loop to continuosly request live values
	while True:
		# query_solmate(route, value, timer_config, mqtt)
		response = smc.query_solmate('live_values', {}, timer_config, mqtt)
		if response != False:
			# add mqtt or other stuff here
			if printing:
				print_request_response(route, response)
			# and wait for the next round
			smc.timer_wait(timer_config, 'timer_live', False)
```

## Run as systemd Service (Linux Only)

When running the Python script on a Linux system using `systemd`, you can automate it on startup.

1. To create a service to autostart the script at boot, copy the content of the example service  
configuration from below into the editor when called in step 2.
2. `sudo systemctl edit --force --full eet.solmate`
3. Edit the path to your script path and for the .env file.  
Also make sure to replace `<your-user>` with the account from which this script should run.
4. Finalize with the following commands:  
`sudo systemctl daemon-reload`  
`sudo systemctl enable --now eet.solmate.service`  
`sudo systemctl status eet.solmate.service` 

```
[Unit]
Description=Python based EET-Solmate to MQTT
After=multi-user.target

[Service]
User=<your-user>
Restart=on-failure
Type=idle
ExecStart=/usr/bin/python3 /home/<your-user>/<your-path>/solmate.py </home/<your-user>/<your-path>/.env>

[Install]
WantedBy=multi-user.target
```

## Home Assistant

### MQTT Sensors

When everything went fine, you will see the solmate as device in MQTT. Note that you will see two `timestamps` by intention. The differentiate the following:

* The first timestamp is updated once every `timer_live` query interval.
* The other timestamp is updated once every nightly scheduled query at 23:45 getting the IP address and SW version only. As these values update quite rarely, there is no need to do that more often. 

Note that both timers are updated on restart. Knowing this you can see if there was an out of schedule program restart due to error handling if the second timer is not at the scheduled interval.

### Energy Dashboard

At the time of writing, the HA energy dashboard has no capability to properly display ANY system where the battery is the central point and only carged by the solar panel respectively is the source of injecting energy. This is not EET specific. A [feature request](https://community.home-assistant.io/t/energy-flow-diagram-electric-power-update-needed/619621) has been filed.

### Template Sensors

These are template examples you can use for further processing when you need to split a single +/- value into variables that can contain only a positive value or zero.
   
```
  # virtual EET Solmate sensors
  - sensor:
    # battery consumption
    # negative values(battery_flow) = charging or 0
    - name: 'Solmate faked Battery Consumption'
      unique_id: 'solmate_faked_battery_consumption'
      unit_of_measurement: 'W'
      device_class: 'power'
      icon: 'mdi:battery-charging-40'
      state: >
        {{ -([ 0, states('sensor.solmate_battery_flow') | float(0) ] | min) }}

    # battery production
    # production = positive values(inject_power) or 0
    - name: 'Solmate faked Battery Production'
      unique_id: 'solmate_faked_battery_production'
      unit_of_measurement: 'W'
      device_class: 'power'
      icon: 'mdi:home-battery-outline'
      state: >
        {{ ([ 0, states('sensor.solmate_inject_power') | float(0) ] | max) }}
```
