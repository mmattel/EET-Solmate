# Standard Preperation

This section is valid when running a dockerized HA or when using a separate host running the solmate script.

* For ease of handling, clone this repo locally using [git clone](https://github.com/git-guides/git-clone) assuming you have installed git and know how to use it. This makes updating to a newer release more easy. As rule of thumb, use your home directory as target.

* Otherwise, manually copy the files to a location of your choice.  
  As rule of thumb, use a folder in your home directory as target.
* Check that all required modules are installed.  
  Run `python check_reqirements.py` to see which are missing.  
  You may need to cycle thru until all requirements are satisified.
* [Configure](#solmate_envpy) the `.env` file.
* Open two shells (assuming you are running a Linux derivate):
  * In the first shell run: `tail -f /var/log/syslog | grep solmate` to monitor logs. <br>
Alternatively set `console_print` in `solmate.py` temporarily to true in the script.
  * In the second shell start the script with `python solmate.py` from the installed location.
* You should now see the script running successfully.  
  If not check the configuration.
* Monitor MQTT posts, use [MQTT Explorer](https://github.com/mmattel/Raspberry-Pi-Setup/tree/main#steps) to do so.  
  The Solmate should show up as `eet/sensor/solmate` (or how you configured it).
* Check that HA shows in MQTT the new SOLMATE/EET device.
* Check [Run as systemd Service (Linux Only)](#run-as-systemd-service-linux-only) for autostarting on boot.
