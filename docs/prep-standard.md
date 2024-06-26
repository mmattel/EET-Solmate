# Standard Preparation

This section is valid when running a dockerized HA or when using a separate host running the solmate script.

* For ease of handling, clone this repo locally using [git clone](https://github.com/git-guides/git-clone) assuming you have installed git and know how to use it. This makes updating to a newer release more easy. As rule of thumb, use your home directory as target.  
**Note** that the directory `solmate` will be created *in the directory you are issuing the command*!

  * Use the following command for a **first clone**:  
    ```
    git clone --depth 1 https://github.com/mmattel/eet-solmate.git solmate
    git fetch --all --tags
    ```
  * Use the following commands **for updates**:  
    Note that this will drop any changes made except configuration.  
    ```
    cd solmate
    git checkout main
    git stash -u && git stash drop
    git pull --rebase origin main
    git fetch --all --tags
    ```
  * Switch to a stable solmate version (example v4.0.0):
    ```
    git tag -l
    git checkout tags/v4.0.0
    ```
* Otherwise, manually copy the files to a location of your choice.  
  As rule of thumb, use a folder in your home directory as target.
* Check that all required modules are installed.  
  Run `python check_reqirements.py` to see which are missing.  
  You may need to cycle thru until all requirements are satisified.
* [Configure](configuration.md) the `.env` file.
* Open two shells (assuming you are running a Linux derivate):
  * In the first shell run: `tail -f /var/log/syslog | grep solmate` to monitor logs. <br>
Alternatively set `console_print` in `solmate.py` temporarily to true in the script.
  * In the second shell start the script with `python solmate.py` from the installed location.
* You should now see the script running successfully.  
  If not check the configuration.
* To monitor MQTT messages, use the [MQTT Explorer](https://github.com/mmattel/Raspberry-Pi-Setup/tree/main#steps) to do so.  
  The Solmate should show up as `eet/sensor/solmate` (or how you configured it), respectively in subsection of `homeassistant/sensor/` etc.
* Check that HA shows in MQTT the new SOLMATE/EET device.
* Check [Run as systemd Service (Linux Only)](#run-as-systemd-service-linux-only) for autostarting on boot.

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
