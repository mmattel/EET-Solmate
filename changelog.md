# Changelog

## [Unreleased]

* Future

## [7.2.5] 2025.04.10

* Fixed a bug introduced with 7.2.4. Two variables were not using the class instance identifyer.

## [7.2.4] 2025.04.06

* Added a logging when either the Solmate or the MQTT server cant be reached anymore. This can happen for example on network outages, when the
  Solmate is offline or is disconnected due to a defect, or the MQTT server is offline. This logging helps to makes it clear where an issue is
  origined, either on the `esham` side or required hardware is not available.

## [7.2.3] 2025.03.21

* Fixing of two edge cases that could crash esham:
  - Backwrite from HA to MQTT before the first initialistation has been completed.
  - The Solmate has not replied with a proper response for boost or injection during the regular query and an MQTT backwrite tries to access these uninitialized variables.

## [7.2.2] 2024.10.03

* Doc changes only for the Appdaemon configuration documentation:
  - Add `production_mode: True` to avoid container log entries like
  `Excessive time spent in utility loop`.
  - Add `missing_app_warnings: 0` to silence found files warnings where there is no related app defined.

## [7.2.1] 2024.10.01

* NO CODE CHANGES\
  Fixed the version number of `esham` which I forgot to update in the last release.  

## [7.2.0] 2024.09.25

* Appdaemon only:
  * Added the `autostart` var which allows to disble starting `esham` automatically on Appdaemon startup.
	  You can manually start `esham` via the switch in HA if configured and `monitor_app` is set
		to `True` (default). See the `solmate_appdaemon_0` file for more and important details.
		If you have multiple solmates running, you must overwrite the code from all `solmate_appdaemon_x`
		files manually.
  * Make monitoring the app independent if `esham` has been started or not, but only dependent on if
		`monitor_app` is set to `True` (default).
  * Prefix Appdaemon log output with `Appdaemon:` for ease of identification.

## [7.1.0] 2024.08.18

* Appdaemon only:
  * Added the ability to start and stop `esham` via a HA entity.
    To do so, you need to create a toggle entity manually in HA first, see the "Install via Appdaemon"
    guide for more details.
  * Fixed `.gitignore` to allow multi Solmate installations which would have been deleted on upgrade
    formerly.

## [7.0.2] 2024.08.04

* Appdaemon only:
  * Fix to prevent the possibility to run multiple instances of the same solmate in parallel.
  * Fix to trigger and catch terminating `esham` on programatical request like with p.terminate()
  * Prevent printing startup status in the Appdaemon log additionally. The app log is not affected.
    For debugging, this can be enforced by setting `general_console_print` to `True`.

## [7.0.1] 2024.08.02

* The Appdaemon integration needed a fix to make `esham` not blocking other apps. This is now fixed
  by making this integration an own and independent thread.
  * As bonus, threading in AD enables by design multi Solmate configurations.
* Adding an upgrade guide
* Adding a migration guide
* Adding a multi Solmate setup guide

## [7.0.0] 2024.07.31

* MAJOR:
  * Allow `esham` to run as Appdaemon app.
  * Deprecating the HA crond installation method in favour of Appdaemon. The crond method will still exist
    but will get removed in a subsequent release, no development efforts will be done anymore. Upgrade
    your installation to use Appdaemon.
  * Implement dynamic loading and importing libraries.
  * Adapt the code to coexist with libraries that are installed with a lower version than needed by `esham`.
    This is in particular implemented for `paho-mqtt` but can be extended for other libraries when necessary.
  * Removing 3 libraries from the requirements: `paho-mqtt`, `semver` and `termcolor`.\
    Note that when not running as Appdaemon app like when using dedicated hardware, it is beneficial
    to install the `paho-mqtt` library because dynamic library loading and importing is not necessary.
  * Note that the pure python installation continue to exists and is a vital part of available methods.
* Switching to [keep a changelog](https://keepachangelog.com).
* Full docs refactoring

## [6.2.0] - 2024-07

* There are no new functionalities BUT:\
  A big refactoring of error handling has been made. Formerly, the program restarted on most of the errors.
  Now they are covered in an ever true while loop. This is especially true for the websocket (solmate)
  or mqtt class . This loop is only exited and the program ended hitting ctrl-c, service stop or an error
  that cant be covered which then is anyways outside the scope. Selecting a minor version jump, because this
  change is relevant.
* The Solmate reboot function now respects the above handling and the log shows correct steps.
* Due to the new error handling, sent values via MQTT during any websocket connection loss are processed
  after reconnection. First in, first out.
* Some internal restructurings, variable improvements and cleanups, improved logging (source: message).
* Authentication failure handling is greatly improved. If login credentials are wrong, the program ends.
* Solmate authentication is going into a timed retry loop, if the first authentication was successful
  but the auth hash response failed. It was most likely temporary and will recover.
* Connection outages will go into a timed retry loop.
* Log with details if a MQTT to Solmate write was reported unsuccessful from the Solmate. 

## [6.1.0] - 2024-07

* On special request, the info section now shows the version of this SW (esham).

## [6.0.0] - 2024-07

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
* Set values via MQTT has been improved and an error handling implemented. You MUST use integer
  (non fractioned numbers) values. See the README for more details.
* Code refactoring
* Documentation refactoring.

## [5.0.0] - 2024-04-29

* With version 5, the following changes have been implemented:
  * Enable some values to be set.
  * Values in HA are now grouped by meaning:\
    **Sensor**, **Config** and **Diagnose**
  * Entities got new names --> **BREAKING**
  * A lot of code improvements and fixes.
  * For more details see the release notes in the tag.

## [4.1.0] - 2024-04-02

* Mainly improve HAOS integration.
* Doc fixes.

## [4.0.2] - 2024-03-08

* Fix MQTT broker consecutive disconnect/connect messages.

## [4.0.1] - 2024-03-03

* Doc fixes.

## [4.0.0] - 2024-02-29

* The documentation got revised.
* Updating some code to be prepared for possible changes in Python and library releases.
* When using HAOS:
    - The scripts run in a Python virtual environment, you need to prepare this yourself.
    - A library needed has been added. This library was not present in HAOS.
    - Adding bash scripts to allow integration via HA shell scripts.
    - Startup and running logs are written into a file as this is not integrateable into HA.
  
## [3.0.0] - 2024-02-25

* The MQTT code has been updated to fully use the capablities of the `paho-mqtt` v2 library.
* A check routine has been added if the v2 library has been installed. The script ends if not.
* When re-running the `check-requirements.py` script, you will get notified about the possibility
to additionally check and update other libraries like websockets. Post running several checks,
it is ok to do so.
* The MQTT code now uses the MQTTv5 protocol but is setup for MQTTv3.x compatibility.

## [2.0.0] - 2023-03-05

* You can now **reboot** your Solmate via HA / MQTT.\
  This is beneficial if the Solmate SW needs a restart and you do not want to get outside.
  Consider that this is only possible if you use the local connection,
  as the internet connection does not provide this API route.
  When using the internet connection, though pressing reboot in HA, no action takes place.  
  This can bee identified as no actions are logged.
* Querying the Solmate is now generally much more stable.\
  The timer used between queries is now asynchron which does not longer block websocket communication.
* You can now use the local connection as default instead using the internet version.\
 Formerly, the local connection was much less stable than the internet one.  
 Using local, you always have access to your Solmate as long there is power and you are more independent
 compared to external server availability.

## [1.0.0] - 2023-12-01

Initial release.
