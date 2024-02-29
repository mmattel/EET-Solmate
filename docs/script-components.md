# Script Components

   * [`solmate.py`](#solmatepy)
   * [`solmate_websocket.py`](#solmate_websocketpy)
   * [`solmate_mqtt.py`](#solmate_mqttpy)
   * [`solmate_utils.py`](#solmate_utilspy)
   * [`solmate_check.py`](#solmate_checkpy)
   * [`solmate_env.py`](#solmate_envpy)
      * [Necessary Data in the '.env' File](#necessary-data-in-the-env-file)

## solmate.py

This is the main program that imports all other components. It also has a proper CTRL-C and SIGTERM handling.

To parametrize, you either can use:

1. the predifined `.env` file, or
2. an own file `python solmate.py <your-env-file>`, or
3. when no envvar file is present, envvars defined via the OS or e.g. docker

There is a job scheduler for jobs (currently only the `get_solmate_info` is defined) that only needs
to run once a day. The responses change rarely, but can, like the Solmates sw-version. The job is
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

## `solmate_websocket.py`

1. Initialize with `smws_conn = smws.connect_to_solmate(merged_config, console_print)`.
2. Authenticate with `response = smws_conn.authenticate()`  
  Note that envvar `eet_server_uri` must be mandatory present, all other stuff will return an auth error. 
3. This returns the connection as response
4. Then either run a plain request with:  
`smc_conn.ws_request(route, data)`  
or a request including proper error handling  
`smc_conn.query_solmate(route, value, merged_config, mqtt)`  
`merged_config` provides waiting times for the next action in case of coverable errors.

## `solmate_mqtt.py`

Without going into much details, to make EET Solmate auto discoverable for Home Assistant, the subroutine `construct_ha_config_message` is called. Do intensively testing when changing stuff here. I recommend using [mqtt Explorer](https://github.com/mmattel/Raspberry-Pi-Setup/tree/main#steps) to monitor the message flow.

## `solmate_utils.py`

Provides the following commonly used routines:

* Define the message queue to process recieved messages from MQTT topics.
* `logging`  
Prints the given message to the console and to syslog - which is useful when running as deamon.
* `timer_wait`  
Waits the given time and logs, in case enabled, that it is waiting for the particular time.
* `restart_program`  
When called, restarts the script like from cmd line. Necessary for unrecoverable errors.

## `solmate_check.py`

This is called at the very beginning post basic setup has been done and checks if library versions needed
are satisfied. At the moment, only the `paho-mqtt` library is checked. Library versions need to be satisfied
to continue. 

## `solmate_env.py`

This reads config data from the `.env` file or a file defined as cmd line argument.
You can also use envvars instead. To force using envvars, no `.env` file must be present or defined
as option on startup.

### Necessary Data in the '.env' File

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

## Known Routes

This is informational only and possibly not complete. All routes have as data `{}` (= no data) except where mentioned

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
