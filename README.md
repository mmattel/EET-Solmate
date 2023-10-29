# EET-Solmate to MQTT Usage Description

A Python script to read data from a EET SolMate and send it to a MQTT broker for the use with Homeassistant.

   * [General Info](#general-info)
   * [Preperation and Quick Start](#preperation-and-quick-start)
   * [Script Components](#script-components)
      * [solmate.py](#solmatepy)
         * [Known Routes](#known-routes)
      * [solmate_websocket.py](#solmate_websocketpy)
      * [solmate_mqtt.py](#solmate_mqttpy)
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

* HA, MQTT and this set of Python scripts are independent units. You need to have as prerequisite HA and MQTT successfully up and running. They can therefore run on separate hosts/containers and connect to each other as configured.

* You can't run this scripts as [HA Python Integration](https://www.home-assistant.io/integrations/python_script/). This solution contains a set of single python files working together and not a single one required by HA. Doubting that making it a single script would work as the necessary error handling will in case restart the script which may negatively interfere with HA.

* You need per solmate installed one instance of the script individually configured (if you have more than one).

* For the time being, you can only send data to MQTT but not recieve data like to configure SolMate.

* Compared to the [solmate SDK](https://github.com/eet-energy/solmate-sdk), the code provided has tons of [error handling](#error-handling) that will make the script run continuosly even if "strange" stuff occurs.

## Preperation and Quick Start

* For ease of handling, clone this repo locally using [git clone](https://github.com/git-guides/git-clone) assuming you have installed git and know how to use it. This makes updating to a newer release more easy. As rule of thumb, use your home directory as target.

* Otherwise, manually copy the files to a location of your choice. As rule of thumb, use a folder in your home directory as target.

* Check that all required modules are installed, run `python check_reqirements.py` to see which are missing.
You may need to cycle thru until all requirements are satisified.

* [Configure](#solmate_envpy) the `.env` file.
* Open two shells (assuming you are running a Linux derivate):
  * In the first shell run: `tail -f /var/log/syslog | grep solmate` to monitor logs. <br>
Alternatively set `console_print` in `solmate.py` temporarily to true in the script.
  * In the second shell start the script with `python solmate.py` from the installed location.
* You should now see the script running successfully. If not check the configuration.
* Monitor MQTT posts, use [MQTT Explorer](https://github.com/mmattel/Raspberry-Pi-Setup/tree/main#steps) to do so. The SolMate should show up as `eet/sensor/solmate` (or how you configured it).
* Check that HA shows in MQTT the new SOLMATE/EET device.

## Script Components

### solmate.py

This is the main program that imports all other components. It also has a proper CTRL-C and SIGTERM handling.

To parametrize, you either can use:

1. the predifined `.env` file, or
2. an own file `python solmate.py <your-env-file>`, or
3. envvars defined via the OS or e.g. docker

Following parameters can be set via the code only and are intended for either development or testing.

* Define `add_log` as required to add any log output for default timers when using loops. Can be set to `False` when running as deamon like with systemd. Note that `live_values` do not need any waiting time to be logged...

* Define `use_mqtt` to globally enable/disable mqtt, makes it easier for testing.

* Define `print_response` to enable/disable console print of the response. Helpful when testing.

* Define `console_print` to enable logging also to console, syslog is always used.

There is a job scheduler for jobs (currently only the `get_solmate_info` is defined) that only need
to run once a day as the response changes rarely, but can, like the solmates sw-version. The job is
forced to run at startup and then on the defined interval.

On successful startup, following messages are logged (exampe):

```
Using env file: .env
Initializing websocket connection...
Authenticating...
Websocket is connected to: wss://sol.eet.energy:9124/
Got redirected to: wss://sol.eet.energy:9125/
Websocket is connected to: wss://sol.eet.energy:9125/
Authentication successful!
SolMate is online.
Initializing the MQTT class.
Initializing the MQTT client.
MQTT is connected and running.
Update MQTT topics for Homeassistant.
Once a day queries called by scheduler.
```

#### Known Routes

All routes have as data {} (= no data) except where mentioned

1. `get_api_info`
2. `get_solmate_info`
3. `live_values`
4. `get_user_settings`
5. `get_grid_mode`
6. `get_injection_settings`	  
note that you must provide proper data as attribute, see `get_api_info` output for more details
7. `logs`  
note that you must provide proper data as attribute, see `get_api_info` output for more details

### `solmate_websocket.py`

1. Initialize with `smc_conn = smc.connect_to_solmate(solmate_config, console_print)`.
2. `smc_conn.authenticate()` with the array configuring solmate from env file or envvar as parameter.  
Note that element `eet_server_uri` must be mandatory present, all other stuff will return an auth error. 
3. this returns the connection as response
4. then either run a plain request with:  
`smc_conn.ws_request(route, data)`  
or a request with error handling  
`smc_conn.query_solmate(route, data, timer_config)`  
the timer_config defines waiting times for the next query in case of coverable errors

`logging` prints the given message to the console and to syslog - which is useful when running as deamon.
`timer_wait` waits the given time and logs, in case enabled, that it is waiting for the particular time.
`restart_program` when called, restarts the script like from cmd line. Necessary for unrecoverable errors.

### `solmate_mqtt.py`

Without going into much details, to make EET Solmate auto discoverable for Home Assistant, the subroutine `construct_ha_config_message` is called. Do intensively testing when changing stuff here. I recommend using [mqtt Explorer](https://github.com/mmattel/Raspberry-Pi-Setup/tree/main#steps) to monitor the message flow.


### `solmate_env.py`

This reads config data from the `.env` file or a file defined as cmd line argument.
You can also use envvars instead.

#### Necessary Data in the '.env' File

As a starting point, make a copy of the `.env-sample` file, name it `.env` and adapt it accordingly.

```
# mqtt config
mqtt_server=<mqtt-address>
mqtt_port=1883
mqtt_username=<mqtt-user>
mqtt_password=<mqtt-password>
mqtt_client_id=solmate_mqtt
mqtt_topic=solmate
mqtt_prefix=eet
mqtt_ha=homeassistant

# solmate config
# get the local address from your dhcp server
# note that local access is good for testing, but does currently not seem to be stable
#eet_server_uri="ws://sun2plug.<your-domain>:9124/"

eet_server_uri="wss://sol.eet.energy:9124/"

eet_serial_number="<solmate-serial-number>"
eet_password="<solmate-password>"
eet_device_id="<solmate-given-name>"

# timer config
# time in seconds

# retry when solmate is offline after
timer_offline=600

# query live values after each x seconds
timer_live=30

# retry when connection got closed after
timer_conn_closed=30

# as number
# when there are too many consecutive response errors, restart after n attempts
# this gives in total waiting time: timer_live [s] x timer_attempt_restart
# 3 * 30 = 90s = 1.5min
timer_attempt_restart=3
```

## Error Handling

Errors are handled on best effort and in **most cases** handed over to the caller to decide.

1. Authentication error: `solmate.py` --> `sys.exit()`
2. `query_solmate` --> `inexistent route` --> `solmate_websocket` --> `sys.exit()`
3. Missing or wrong `data` in request --> `query_solmate` --> `send_api_request` --> `ConnectionClosedOK` -->  
watch the log, it will continue after the waiting time. Can't be covered due to missing details in the response!
4. When the `response` returned `False` --> `query_solmate` --> continue but count the number of consecutive errors. Restart after `timer_attempt_restart` attempts.
5. You will see moste likely regular automatically program restarts due to a websocket error raised:
`sent 1011 (unexpected error) keepalive ping timeout; no close frame received`. See [What does ConnectionClosedError: sent 1011 (unexpected error)](https://websockets.readthedocs.io/en/stable/faq/common.html#what-does-connectionclosederror-sent-1011-unexpected-error-keepalive-ping-timeout-no-close-frame-received-mean) for details. The program covers the error and restarts completely.

For those who are interested in the details of `sent 1011`: There seems to be an impact on the configuration in the websocket code. The websocket `ping_timeout` which defaults to 20s is lower than `timer_live` which defaults to 30s.
It is maybe not a good idea to have them on the same value and a ping should be more frequent than
regular recurring requests. For a long term solution, the server (both variants of `eet_server_uri` in the config, this is on the EET side!), should handle ping/pong requests properly. Currently they are _not that stable_ triggering the error handling.

While connecting to the external server of EET is a bit more stable and coverable errors are in the timeframe of hours, you will see when directly connecting to the local solmate errors in the interval of some minutes. Both issues have been raised to EET and agreed to be valid, but no solution has been provided so far. It is therefore recommended to use the external EET server for queries and not the solmate directly, though that solution would be preferred avoiding not necessary internet traffic.

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
