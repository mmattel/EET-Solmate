# EET-Solmate with HomeAssistant via MQTT

Integrate EET SolMate with Homeassistant using MQTT (read AND write!)

Internal name: `esham` --> **E**et **S**olmate **H**ome**A**ssistant **M**qtt

<a href="https://www.buymeacoffee.com/martin.mattel" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>

   * [General Info](#general-info)
   * [Code Changes](#code-changes)
   * [Prerequisites](#prerequisites)
   * [Installation Options](#installation-options)
   * [Configuration](#configuration)
   * [Migration](#migration)
   * [Upgrading](#upgrading)
   * [Multiple Solmates](#multiple-solmates)
   * [Connection Resilience](#connection-resilience)
   * [MQTT Monitoring](#mqtt-monitoring)
   * [Additional Home Assistant Info](#additional-home-assistant-info)
   * [Known Routes](#known-routes)

## General Info

`esham` is a Python based program that integrates [EET Solmate](https://www.eet.energy) with
[Home Assistant](https://www.home-assistant.io) (HA) via [MQTT](https://mqtt.org).

Data flow is bidirectional. This means, that not only the Solmates gets queried and the data is provided
and shown in HA as entities, you can also send back data from HA via MQTT to the Solmate. With the
ability to send back data, you can dynamically adapt injection settings based on  defined criterias
calculated in HA (like when using [Node-RED](https://nodered.org).

**Mentionalbe Features:**

* **Easy to Deploy and Maintain**
  * After installing, configuration and starting, everythings runs fully automated.
* **Connectivity**
  * Connects to the Solmate directly or via the EET provided cloud.\
    Note that the EET API provides feature connection dependent like reboot which is only local
	available. API differences are handled automatically and show up in HA correctly.
  * Connects to either an external or the HA MQTT broker addon.
* **Handle Spare Systems**
  * When a Solmate needs to be returned for repair due to a technical issue and you get a spare system,
    you can define an extra serial number for the spare or replacement Solmate, no HA entity will change.
* **Installation Options**
  * Multiple installation options are provided (see below)
* **Stability**
  * Beside upgrades done, I have not experienced an outage for more than 1 year.
  * Fault tolerance with connectivity issues or outages.
  * Writebacks from HA to the Solmate get buffererd in case the connection to the Solmate has an outage.
* **Multiple Solmates**
  * You can configure more than one Solmate.
    * For plain Python installations, each Solmate runs in its own directory and is therefore fenced.
	* For Appdaemon, each Solmate needs it AD config, but they will run using the same code but as
	  individual thread.
* **Logging**
  * `esham` provides logging but only for important stuff. Daily business is not logged except configured.
* **Configurabiliity**
  * Beside mandatory data to be entered like for hosts and authentication, the majority of
    configuration options is preset without polluting the config file but can be added and reconfigured
	on demand.
* **Ressource Efficiency**
  * When running, `esham` has a minimum foodprint and a very low CPU usage.
* **Python Versions**
  * Tested and runs with Python 9 to Python 12


**Installation Options**

`esham` can be installed in 2 different ways:

* As plain Python program that runs on independent hardware
* As app in Appdaemon:
  * Either integrated in HA (!!) like when using a HA Appliance.
  * Or when installing Appdaemon as seperate container.
  * See the HA [Installation](https://www.home-assistant.io/installation) options for more details.

* You need per Solmate installed, one instance of the script individually configured, Note that you
  need some additionals steps when using HAOS by adapting the AD config and entry scripts used accordingly.

## Code Changes

* **Breaking Changes**\
  See the [breaking changes](./breaking.md) for more details.

* **Important Improvements**\
  See the [changelog](./changelog.md) for more details.

## Prerequisites

Before installing `esham`, you must have:

* A HA Appliance or a HA installation up and running.
* A MQTT broker, either as addon or as external container up and running

## Installation Options

* **Install via Plain Python**\
  Use this method when you want to run `esham` fully independent on a host that has Python installed.
  See the [Plain Install Option](./docs/plain-install.md) documentation for more details.

* **Install via Appdeamon**\
  Dependent on the way how [HA is installed](https://www.home-assistant.io/installation), you can either
  directly integrate `esham` as app in the appdeamon addon or use a dedicated appdeamon container running
  on a separate host. See the [Appdaemon](./docs/appdaemon.md) documentation for more details.

## Configuration

See the [configuration](./docs/configuration.md) documentation for more details.

## Migration

See the [migration](./docs/migration.md) documentation for more details.

## Upgrading

See the [upgrade](./docs/upgrade.md) documentation for more details.

## Multiple Solmates

See the [multiple Solmates](./docs/multi-solmates.md) documentation for more details.

## Connection Resilience

If a first connection and authentication on startup was successful to both worlds
(Solmate via websocket, MQTT), any disconnect will initiate a reconnect. While this is easy with
MQTT as it has this functionality perfectly embedded even if you shut down/restart the MQTT host,
it is a bit more complicated with websocket required for the Solmate. If the connection can be
reestablished by websocket automatically again, things are the same as with MQTT. But if this is
not possible, for example if you reboot the Solmate and the connection is temporary gone, you can
only act when trying to access websocket and deal with the error reported.

This means that a connection loss to the Solmate can only be recognized by accessing it like with
regular query interval or setting a value via HA/MQTT.

You will therefore see that multiple timers are acting in sequence when a Solmate connection loss
occurs. Depending on the incident, different timers and reconnection methods are used. As more
sever, as longer it will take, but it will.

## MQTT Monitoring

See the linked [description](./docs/monitor-mqtt.md) documentation for more details.

## Additional Home Assistant Info

See the linked [description](./docs/additional-ha-info.md) documentation for more details.

## Known Routes

Intedned as optional info, see the linked [description](./docs/known-routes.md) for more details.
