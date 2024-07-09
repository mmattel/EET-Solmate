# EET-Solmate with HomeAssistant / MQTT

Integrate EET SolMate with Homeassistant using MQTT (read AND write!)

Internal name: `esham` --> **E**et **S**olmate **H**ome**A**ssistant **M**qtt

<a href="https://www.buymeacoffee.com/martin.mattel" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>

   * [General Info](#general-info)
   * [Upgrading - Breaking Changes](#upgrading---breaking-changes)
   * [Important Improvements](#important-improvements)
   * [Preparation and Quick Start](#preparation-and-quick-start)
   * [Preparation for HAOS](#preparation-for-haos)
   * [Configure the Script](#configure-the-script)
   * [Home Assistant](#home-assistant)
      * [MQTT Sensors](#mqtt-sensors)
      * [Energy Dashboard](#energy-dashboard)
      * [Template Sensors](#template-sensors)
      * [Total Solar Injection](#total-solar-injection)
   * [Set Values via MQTT](#set-values-via-mqtt)
   * [Script Components](#script-components)
   * [Known Routes](#known-routes)

## General Info

**IMPORTANT INFORMATION:**

* HA, MQTT and this set of Python scripts are **independent units**.  
  You need to have as prerequisite HA with MQTT setup and a MQTT broker successfully up and running.
  They can also run on separate hosts/containers and be connected to each other.

* The minimal Python version supported is Python 9 and works the latest Python libraries.

* **NEW** since version 6: you **can** define an extra serial number for a spare or replacement Solmate.\
Note that there are also new functionalities and breaking changes.

* **NEW** since version 5: you **can** write back data from HA via MQTT to the Solmate!

* **NEW** since version 4: you **can** run these scripts as [HA Shell Command](https://www.home-assistant.io/integrations/shell_command/).  
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

## Upgrading - Breaking Changes

See the [breaking changes](./breaking.md) for details.

## Important Improvements

See the [changelog](./changelog.md) for details.

## Preparation and Quick Start

This section is valid when running a dockerized HA or when using a separate host running the solmate script.

See the [Standard](./docs/prep-standard.md) description for details.

## Preparation for HAOS

When running HAOS you **can** prepare the environment to autostart the solmate script.

See the [HAOS - solmate](./docs/prep-ha.md) description for details.

## Configure the Script

See the [configuration](./docs/configuration.md) description for details.

## Home Assistant

### MQTT Sensors

When everything went fine, you will see the Solmate as device in MQTT.

Sensor names are prefixed with an abbreviation of the route for ease of identification. This makes it much easier to identify _where_ a sensor comes from and group it accordingly. Examples: `live_pv_power` or `get_injection_user_maximum_injection`.

Most of the sensors shown originate from the Solmate but not all. The following sensors are created artificially and add information about the Solmate connected:

* `info_esham_version`\
  Shows the version of this software.
* `info_connected_to`\
  This shows where the solmate is connected to, either `local` or `cloud`.
* `info_operating_state`\
  This either shows `online` or `rebooting`.
* `info_timestamp`\
  There are two timestamps shown, for details see below.
* `button_reboot`\
  This is a button you can click to reboot the Solmate. Note that this is only functional if the Solmate
  is connected locally. Though clickable, it will not work when connected to the server as the server does
  currently not provide the API. As an easy reminder where connected to, check `info_connected_to`.

The two `x_timestamps` are by intention. The differentiate the following:

* `live_timestamp` is updated once every `timer_live` query interval.
* `info_timestamp` is artificial and updated once every nightly scheduled query at 23:45\
  Here only info stuff is queried. As these values update quite rarely,
  there is no need to do that more often. 

Note that both timers are updated on restart. Knowing this you can see if there was a program restart due to error handling if the second timer is not at the scheduled interval.

### Energy Dashboard

At the time of writing, the HA energy dashboard has no capability to properly display ANY system where the battery is the central point and only carged by the solar panel respectively is the source of injecting energy. This is not EET specific. A [feature request](https://community.home-assistant.io/t/energy-flow-diagram-electric-power-update-needed/619621) has been filed. You can add your vote if you want to push this.

### Template Sensors

These are template examples you can use for further processing when you need to split a single +/- value into variables that can contain only a positive value or zero or when using a Riemann Integration (see below). As suggestion, use the same value prefix in unique_id as defined in `mqtt_topic` from the `.env` file.

Note to reboot HA to make template sensors available.
   
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
        {{ -([ 0, states('sensor.solmate_live_battery_flow') | float(0) ] | min) }}

    # battery production
    # production = positive values(inject_power) or 0
    - name: 'Solmate faked Battery Production'
      unique_id: 'solmate_faked_battery_production'
      unit_of_measurement: 'W'
      device_class: 'power'
      icon: 'mdi:home-battery-outline'
      state: >
        {{ ([ 0, states('sensor.solmate_live_battery_floww') | float(0) ] | max) }}

    # injection power (to be independent of entity name changes) to be used in riemann integral
    # production = positive values(inject_power) or 0
    - name: 'Solmate faked Injection Power'
      unique_id: 'solmate_faked_inject_power'
      unit_of_measurement: 'W'
      device_class: 'power'
      icon: 'mdi:transmission-tower-import'
      state: >
        {{ ([ 0, states('sensor.solmate_live_inject_power') | float(0) ] | max) }}

```

### Total Solar Injection

The Solmate does not provide an aggregated total solar injection value. This needs to be added manually in HA.

If not already done, add a new Integration: [Riemann sum integral](https://www.home-assistant.io/integrations/integration/).
The "bad" thing on RI is, if there is a change in the underlaying source which you cant configure anymore, you loose the sum/history and you start counting from 0 because you cant preset it. To overcome this situation, Create a template sensor as source, see the section above, to avoid this situation (the source can be changed at any time). Alternatively edit the `config/.storage/core.config_entries` file and replace the source (...).

The following settings need to be made, adapt them according your needs. Either do this by adding a yaml config or directly via the Riemann Integration GUI:

```yaml
sensor:
  - platform:            integration
    state_class:         total
    source:              sensor.solmate_faked_injection_power
    unit_of_measurement: kWh
    device_class:        energy
    icon:                mdi:chart-histogram
    friendly_name:       Solmate Total Injection
    method:              left
    round:               2
    unit_prefix:         k
    unit_time:           h
```

## Set Values via MQTT

Some values can be set via MQTT like injection or boost.

**IMPORTANT:**\
These values MUST BE plain integer numbers WITHOUT any decimal or thousand separator.
For the time being, only positive fractionless numbers are allowed. Omit leading + or - symbols.
The values are tried to be casted by the program to integer. It is very likely, that when defining
values using dot and comma, language settings mix them up and the cast can't succeed. In this case,
the LAST KNOWN working value will be used instead and a warning will be logged !

**TIPS:**
- When using the incoming new values event (MQTT or HA) to calculate new Solmate settings,
have a small delay like 1 second before updating them via MQTT.
- Only send values if they have changed.
- Before going productive with dynamic settings, check the log of the python script for possible errors responded by the Solmate and fix them.

**INFO:**\
The script processes the outgoing and incoming messages the following way:
1. The loop interval to check for new values from the Solmate is defined by `timer_live` and defaults to 30s.
2. A recieved MQTT message interrupts that timer and processing the loop starts.
3. The loop first checks for messages recieved from MQTT and sends them to the solmate.
4. Then all real and artificial values from the Solmate are queried respectively generated and sent to MQTT.
5. Finally, the timer is restarted.

### BOOST

Boosting is **not** the same way implemented as on the Solmates's webUI. There, setting handling is implemented
in the browser code and not in the Solmate. This mechanism is quite complex to handle and you can't just
preset the values and then trigger start/stop boosting via the API.

To overcome this, the implementation is as follows, follow the steps carefully:
- Set the boost timer to 0.
- Set the boost wattage.
- Set the boost timer to a non zero value - Boost starts now automatically.
- Set the boost timer to 0 to stop boosting if it is in boost mode (remaining time > 0).

The procedure above is very close to the Solmates internal webUI code but omits a boost start/stop button.

Frankly speaking, as long there is no proper API route implementation, avoid using boost via the program.

### Node Red

Using Node Red or any other mechanism to write back injection values (or others when added later):

- Read the important information about the value type from above!
- When calculating a value and writing it back, have a minimum delay like 1s before writing the next one
from the SAME calculation.
- The default setting of 30s to query the Solmate is a good rule of thumb.\
Shorter intervals do not make a lot of sense.
- Note that writing back also triggers a consecutive read after writing (else you would not see updates).
- After finishing all write backs from one cycle, implement some wait for the next query/set
cycle to avoid possible oscillation.

## Script Components

See the linked [description](./docs/script-components.md) for details.

## Known Routes

See the linked [description](./docs/known-routes.md) for details.
