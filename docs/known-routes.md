# Known Routes

This is informational only and possibly not complete. All routes have as data `{}` (= no data) except where mentioned

1. `get_api_info`
2. `get_solmate_info`
3. `live_values`
4. `get_user_settings`
5. `get_grid_mode`
6. `get_injection_settings` and `set_injection_settings`  
  Note that you must provide proper data as attribute, see `get_api_info` output for more details.
7. `logs`  
  Note that you must provide proper data as attribute, see `get_api_info` output for more details.
9. `shutdown`  
  This route has a data attribute like `{'shut_reboot': 'reboot'}` but can only be used when connected locally. 
10. `set_system_time`  
  This route has a data attribute like `{datetime: n}` where  
  `const e = On()()`, `n = e.utc().format(t)` and `t = "YYYY-MM-DDTHH:mm:ss"` (using javascript as base)
11. `get_boost_injection` and `set_boost_injection`
  This routes are (currently) not part of the get_info response.
  Important, when setting boost, you must write both keys `time` and `wattage` in one call! Additionally,
  activating boost is not a binary trigger in the solmate using a key, but a frontend defined behaviour.
  When time is 0, you can predefine wattage without triggereing it. To start boost, you must write time
  with a value <> 0. To stop boost, you must write time with zero, and remember the wattage formerly
  set... (Totally nuts).

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
