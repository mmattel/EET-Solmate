# Monitor MQTT Messaging

Monitoring messaging is not only interresting, you can also see when and which messages have been published.
In addition, you can manually publish messages for testing purposes - experienced users only.

Note that the [MQTT Explorer](https://github.com/mmattel/Raspberry-Pi-Setup/tree/main#steps) is not available
as HAOS addon and must be installed as extra docker container outside HAOS. The link provided contains a
compose file for easy installation. You can search Google for other information how to install.


* Install the MQTT Explorer.
* Connect the MQTT Explorer to the MQTT Broker as configured.
* If the Solmate is already connected, it should show up as `eet/sensor/solmate` (or how you configured it),
  respectively in other subsections of `homeassistant/`.
