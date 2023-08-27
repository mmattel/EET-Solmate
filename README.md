# EET-Solmate to MQTT Usage Description

A Python script to read data from a EET SolMate and send it to a MQTT broker for the use with Homeassistant.

## General Info

Check that all required modules are installed, use `check_reqirements.py` to see which are missing.
You may need to cycle thru until all requirements are satisified.

**IMPORTANT**: You need one Python script configured per solmate installed (if you have more than one).

**IMPORTANT**: For the time being, you can only send data to MQTT but not recieve data like to configure SolMate.

## solmate.py

This is the main program that imports all other components. It also has a proper CTRL-C handling.

To parametrize, you either can use:

1. the predifined `.env` file, or
2. an own file `python solmate.py <your-env-file>`, or
3. envvars defined via the OS or e.g. docker

Define `add_log` as required to add any log output for default timers when using loops.
Can be set to `False` when running as deamon like with systemd.
Note that `live_values` do not need any waiting time to be logged...

Define `enable_mqtt` to globally enable/disable mqtt, makes it easier for testing.

Define `print_response` to enable/disable console print of the response. Helpful when testing.

Defint `console_print` to enable logging also to console, syslog is always used.

There is a job scheduler for jobs (currently only the 'get_solmate_info' is defined) that only need
to run once a day as the response changes rarely, but can like the solmates sw-version. The job is
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

### Possible Routes

All routes have as data {} (= no data) except where mentioned

1. `get_api_info`
2. `get_solmate_info`
3. `live_values`
4. `get_user_settings`
5. `get_grid_mode`
6. `get_injection_settings`	 
note that you must provide proper data as attribute, see get_api_info output for more details
7. `logs`  
note that you must provide proper data as attribute, see get_api_info output for more details

## solmate_websocket.py

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

### Error Handling

Errors are handled on best effort and in **most cases** handed over to the caller to decide.

1. Authentication error: `solmate.py` --> `sys.exit()`
2. `query_solmate` --> `inexistent route` --> `solmate_websocket` --> `sys.exit()`
3. Missing or wrong `data` in request --> `query_solmate` --> `send_api_request` --> `ConnectionClosedOK` -->  
watch the log, it will continue after the waiting time. Can't be covered due to missing details in the response!
4. When the `response` returned `False` --> `query_solmate` --> just wait the `timer_response` and continue

You will see moste likely regular automatically program restarts due to a websocket error raised:
`sent 1011 (unexpected error) keepalive ping timeout; no close frame received`
See [What does ConnectionClosedError: sent 1011 (unexpected error)](https://websockets.readthedocs.io/en/stable/faq/common.html#what-does-connectionclosederror-sent-1011-unexpected-error-keepalive-ping-timeout-no-close-frame-received-mean)
for deatils. Though the program covers the error and restarts completely, it has an impact on configuration.
The websocket `ping_timeout` which defaults to 20s is lower than `timer_live` which defaults to 30s.
It is maybe not a good idea to have them on the same value and a ping should be more frequent than
regular recurring requests. For a long term solution, the server should handle ping/pong requests properly.
Also see the envvar `timer_response_restart` in the `.env` description below for additional details.

## solmate_env.py

This reads config data from the `.env` file or a file defined as cmd line argument.
You can also use envvars instead.

### Necessary Data in the '.env' File

```
# solmate config
# get the local domain from your network setup (router, dhcp etc.)
eet_server_uri="ws://sun2plug.<your-domain>:9124/"

# 'eet_network' is only necessary when accessing from the local network, in combination with the URI above
# when the solmate is local, it does not respond with 'online' compared to server access. as long the
# response does not change, we need that workaround. 
eet_network='local'

# #eet_server_uri="wss://sol.eet.energy:9124/"

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

## Example Calls

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

## Homeassistant

[power-flow-card-plus](https://github.com/flixlix/power-flow-card-plus)

[energy-flow-card-plus](https://github.com/flixlix/energy-flow-card-plus)

[How to integrate energy](https://www.home-assistant.io/integrations/integration/#energy)
