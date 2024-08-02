# Configuring Multiple Solmates

You can configure multiple Solmates, there is technically only a RAM and CPU limit.

## Plain Python

* Clone `esham` for each Solmate you want to connect into an own directory but select unique names.
See the [Download and Update esham Using git](./download-with-git.md) guide how to do so.
* Create a new `.env` file from the `.env-sample` and configure it.
* Create a new systemd setup as described in [Install via Plain Python](./plain-install.md) and start it.

## Appdaemon

Note, make youself a name scheme for different Solmates like using the last 3-4 digits from the SN# as identifyer.
The name scheme will replace `_0` with whatever you have selected.

You do not need to create a new folder for each Solmate! This means that updates only need to be applied once.

* As usual with Appdaemon, before doing any changes, it MUST be stopped!
* For a new Solmate:
  * Extend the `apps.yaml` file with a new entry using the name scheme.
  * Copy the existing `solmate_appdaemon_0.py` and replace `_0` with a value from the name scheme.
  * Edit that file and apply the name scheme to:
    `env_name_appendix` and the `Class` name.
  * Create a configuration file, configure it and apply the name scheme to its file name.
  * Edit `appdaemon.yaml` and add a new log entry with the name scheme applied.

* Start Appdaemon
* Watch the Appdaemon log and the `solmate_log_xxx` in the AD admin console if all went well.

If the setup or the configuration errors, STOP Appdaemon and fix it.
