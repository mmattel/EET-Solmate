# Changelog

* With version 6, the following changes have been implemented:
  * Rework of BOOST and INJECTION handling. See the HA section in README the for more and important details.
  * MQTT has now an error handling if the connection was initially not startable.
    If the connection was once established, it reconnects automatically.
  * Add the ability for a spare/replacement Solmate. See the `.env-sample` file for more details.
  * Add new optional envvars to define limits. See the `.env-sample` file for more details.
  * Global envvars are now optional, you can safely remove them from your config except for those
    where you have deviated settings. See the `.env-sample` file for more details.
  * Timer envvars are now optional, you can safely remove them from your config except for those
    where you have deviated settings. See the `.env-sample` file for more details.
  * The envvar `general_add_log` has been removed as it was not used in the code.
    It was an orphand from ancient times.
  * The newly added envvar `general_console_timestamp` will add a timestamp to the console printout.
  * Code refactoring
  * Documentation refactoring.
* With version 5, the following changes have been implemented:
  * Enable some values to be set.
  * Values in HA are now grouped by meaning:\
    **Sensor**, **Config** and **Diagnose**
  * Entities got new names --> **BREAKING**
  * A lot of code improvements and fixes.
  * For more details see the release notes in the tag.
* With version 4, the following changes have been implemented:
  * The documentation got revised.
  * Updating some code to be prepared for possible changes in Python and library releases.
  * When using HAOS:
      - The scripts run in a Python virtual environment, you need to prepare this yourself.
      - A library needed has been added. This library was not present in HAOS.
      - Adding bash scripts to allow integration via HA shell scripts.
      - Startup and running logs are written into a file as this is not integrateable into HA.
  
* With version 3, the following changes have been implemented:
  * The MQTT code has been updated to fully use the capablities of the `paho-mqtt` v2 library.
  * A check routine has been added if the v2 library has been installed. The script ends if not.
  * When re-running the `check-requirements.py` script, you will get notified about the possibility
  to additionally check and update other libraries like websockets. Post running several checks,
  it is ok to do so.
  * The MQTT code now uses the MQTTv5 protocol but is setup for MQTTv3.x compatibility.

* With version 2.x, the code has been refactored and contains the following major improvements:
  * You can now **reboot** your Solmate via HA / MQTT.  
  This is beneficial if the Solmate SW needs a restart and you do not want to get outside.
  Consider that this is only possible if you use the local connection,
  as the internet connection does not provide this API route.
  When using the internet connection, though pressing reboot in HA, no action takes place.  
  This can bee identified as no actions are logged.
  * Querying the Solmate is now generally much more stable.  
   The timer used between queries is now asynchron which does not longer block websocket communication.
  * You can now use the local connection as default instead using the internet version.  
   Formerly, the local connection was much less stable than the internet one.  
   Using local, you always have access to your Solmate as long there is power and you are more independent
   compared to external server availability.
