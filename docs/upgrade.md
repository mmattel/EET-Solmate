# Upgrading

Independent of the installation method used, shut down `esham` by either stopping the systemd
service or by stopping the Appdeamon appon/container.

When you have cloned this repository as described in
[Download and Update esham Using git](./download-with-git.md), follow the item
**Commands for updates** and the subsequent one **Switch to the solmate version**.

## Plain Python Upgrading

* If you have used the cloned git directory directly to run `esham`, you can restart it now.
* If you separated cloning from production, delete all `solmate*.py` files and copy them from
  the clonded directory.

Start `esham` as you defined startup.

## Appdaemon Upgrading

**IMPORTANT**\
Appdaemon MUST be in shut down state to upgrade!

* **Appdaemon Addon**
  * Connect with `SAMBA` to your HA instance and change into the
    `addon_configs\xxxx_appdaemon\apps\solmate` directory.

* **Appdaemon Container**
  * Change into the config directory defined as volume
    `<local config path>/apps/solmate`.

* Delete all files with pattern `solmate*.py`.
* Copy all files with that pattern from the cloned directory.

Start `esham` by either starting the addon or the container.
