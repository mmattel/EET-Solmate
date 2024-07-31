# Install via Plain Python

This section is valid when running a dockerized HA or when using a separate host running the solmate script.

   * [Preparation Steps](#preparation-steps)
   * [Run as systemd Service (Linux Only)](#run-as-systemd-service-linux-only)

Most easiest, use git for getting `esham`. For details see:
[Download and Update esham Using git](download-with-git.md). The download will be saved on your local device.

## Preparation Steps

* **Check that all required modules are installed.**\
  * Run `python check_reqirements.py` to see which are missing.
    You may need to cycle thru until all requirements are satisified.
* **Configuration**\
  * [Configure](configuration.md) the `.env` file.
* **Start the Program**
  * Start the script with `python solmate.py` from the installed location to test if it startsup correctly.
* **Monitoring**
  * You should now see the script running successfully as it logs the progress, if not check the configuration.
  * Run `tail -f /var/log/syslog | grep solmate` to monitor the syslog if you run the script in the background.

## Run as systemd Service (Linux Only)

When running the Python script on a Linux system using `systemd`, you can automate it on startup.

To create a service to autostart the script at boot, copy the content of the example service
configuration from below into the editor opened.

1. `sudo systemctl edit --force --full eet.solmate`
2. Edit the path to your script path and for the .env file.\
   Also make sure to replace `<your-user>` with the account from which this script should run.
3. Finalize with the following commands:  
   `sudo systemctl daemon-reload`  
   `sudo systemctl enable --now eet.solmate.service`  
   `sudo systemctl status eet.solmate.service` 

**Example service setup**
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
