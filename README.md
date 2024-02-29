# EET-Solmate with HomeAssistant / MQTT

A Python script to read data from a EET SolMate and send it to a MQTT broker for the use with Homeassistant.

   * [General Info](#general-info)
   * [Upgrading - Breaking Changes](#upgrading---breaking-changes)
   * [Important Improvements](#important-improvements)
   * [Preperation and Quick Start](#preperation-and-quick-start)
   * [Preperation for HAOS](#preperation-for-haos)
   * [Script Components](#script-components)
   * [Error Handling](#error-handling)
   * [Known Routes](#known-routes)
   * [Example Calls](#example-calls)
   * [Run as systemd Service (Linux Only)](#run-as-systemd-service-linux-only)
   * [Home Assistant](#home-assistant)
      * [MQTT Sensors](#mqtt-sensors)
      * [Energy Dashboard](#energy-dashboard)
      * [Total Solar Production](#total-solar-production)
      * [Template Sensors](#template-sensors)

## General Info

**IMPORTANT INFORMATION:**

* HA, MQTT and this set of Python scripts are **independent units**.  
  You need to have as prerequisite HA with MQTT setup and a MQTT broker successfully up and running.
  They can and should therefore run on separate hosts/containers and connect to each other as configured.

* **NEW** since version 4: you **can** run this scripts as [HA Shell Command](https://www.home-assistant.io/integrations/shell_command/).  
  Though HA shell commands terminate hard by HA post 60s runtime, I have found a way to make it possible...
  Only a view steps need to be taken and it works, at least in my docker environment which should not be different from HAOS. Libraries needed are reboot persistent and do not conflict with shipped HA libraries. This enables a
  startup on reboot via automation!

* You **can't** run this scripts as [HA Python Integration](https://www.home-assistant.io/integrations/python_script/).  
  This solution contains a set of python files working together and not a single one required by HA.
  Doubting that making it a single script would work as the necessary error handling will in case restart
  the script which may negatively interfere with HA.

* You need per Solmate installed, one instance of the script individually configured (if you have more than one). Note that you need some additionals steps when using HAOS by adapting the scripts used accordingly.

* Stability  
  Compared to the [solmate SDK](https://github.com/eet-energy/solmate-sdk), the code provided has tons of [error handling](#error-handling) that will make the script run continuosly even if "strange" stuff occurs.

* The scripts uses and works the latest Python libraries.

## Upgrading - Breaking Changes

See the [breaking changes](./breaking.md) for details.

## Important Improvements

See the [changelog](./changelog.md) for details.

## Preperation and Quick Start

This section is valid when running a dockerized HA or when using a separate host running the solmate script.

See the [Standard](./docs/prep-standard.md) description for details.

## Preperation for HAOS

When running HAOS you **can** prepare the environment to autostart the solmate script.

See the [HAOS - solmate](./docs/prep-ha.md) description for details.

## Script Components

See the [description](./docs/script-components.md) for details.

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

When everything went fine, you will see the Solmate as device in MQTT.

Most of the sensors shown originate from the Solmate but not all. The following sensors are created artificially and add information about the Solmate connected:

* `connected_to`  
  This shows where the solmate is connected to, either `local` or `server`.
* `operating_state`  
  This either shows `online` or `rebooting`
* `timestamp`  
  There are two timestamps shown, for details see below.
* `reboot`  
  This is a button you can click to reboot the Solmate. Note that this is only functional if the Solmate
  is connected locally. Though clickable, it will not work when connected to the server as the server does
  currently not provide the API. As an easy reminder where connected to, check `connected_to`.

The two `timestamps` are by intention. The differentiate the following:

* The first timestamp is updated once every `timer_live` query interval.
* The other timestamp is updated once every nightly scheduled query at 23:45  
  Here only the IP address and SW version are queried. As these values update quite rarely,
  there is no need to do that more often. 

Note that both timers are updated on restart. Knowing this you can see if there was a program restart due to error handling if the second timer is not at the scheduled interval.

### Energy Dashboard

At the time of writing, the HA energy dashboard has no capability to properly display ANY system where the battery is the central point and only carged by the solar panel respectively is the source of injecting energy. This is not EET specific. A [feature request](https://community.home-assistant.io/t/energy-flow-diagram-electric-power-update-needed/619621) has been filed. You can add your vote if you want to push this.

### Total Solar Production

The Solmate does not provide an aggregated total solar production value. This needs to be added in HA manually.

If not already done, add a new Integration: [Riemann sum integral](https://www.home-assistant.io/integrations/integration/).

The following settings need to be made, adapt them according your needs:
```
state_class:         total
source:              sensor.solmate_pv_power
unit_of_measurement: kWh
device_class:        energy
icon:                mdi:solar-power
friendly_name:       Solar Production
method:              left
round:               2
unit_prefix:         k
unit_time:           h
```

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
