# Notes for Coding Agents

This file gives coding agents (Claude Code, Codex, Copilot, ...) the context needed to work on
`esham` and to update a running installation. `AGENTS.md` is a symlink to this file.

User facing documentation is in [README.md](./README.md) and the [docs](./docs) folder. Read the
relevant part there before changing behavior.

## Project Overview

`esham` (**E**et **S**olmate **H**ome**A**ssistant **M**qtt) connects one or more EET SolMates
(websocket API, local or via the EET cloud) with Home Assistant via MQTT, in both directions.

It runs in one of two ways:

* **Plain Python:** `solmate.py` is the entry point, configured by a `.env` file in the same directory.
* **AppDaemon app:** `solmate_appdaemon_0.py` is the AppDaemon starter. It starts `esham` as a separate
  process (`multiprocessing`, start method `fork`) and optionally lets HA start/stop it via an
  `input_boolean` named like the starter file (`solmate_appdaemon_0`). The configuration file is
  `.env_0` (suffix = `env_name_appendix` in the starter).

| Module | Purpose |
|---|---|
| `solmate.py` | Entry point for plain Python |
| `solmate_appdaemon_0.py` | AppDaemon starter (template for further SolMates `_1`, `_2`, ...) |
| `solmate_appdsolmate.py` | Wrapper that runs `solmate_main.main()` inside the AppDaemon process |
| `solmate_appdmonitor.py` | Start/stop via the HA toggle entity |
| `solmate_main.py` | Main loop, holds `version` |
| `solmate_env.py` | Reads the `.env` file, sets defaults for optional keys |
| `solmate_websocket.py` | SolMate websocket connection (local and cloud) |
| `solmate_mqtt.py` | MQTT connection, HA discovery and write back |
| `solmate_ha_config.py` | HA MQTT discovery messages (entities) |
| `solmate_connect.py` | Connection setup and route checks |
| `solmate_importmanager.py` | Installs/imports a fitting `paho-mqtt` version into `my_packages/` |
| `solmate_utils.py` | Logging, timers, helpers |
| `appdaemon_config/` | Example AppDaemon files (`appdaemon.yaml`, `apps.yaml`, compose) |

## Rules for Changes

* **Never read, print or commit `.env*` files** (except `.env-sample`). They contain SolMate serial
  numbers, passwords and MQTT credentials.
* Indentation is **tabs**, strings use single quotes. Keep the existing style.
* Supported Python: 3.9 up to 3.14. Do not use syntax or library features that break 3.9.
  * `websockets`: use the asyncio client (`websockets.asyncio.client`) and keep the fallback to the
    legacy client for websockets < 13.0.
  * Keep the explicit `fork` start method in the AppDaemon starter. Python 3.14 defaults to
    `forkserver` on Linux, which cannot pickle the AppDaemon app object.
* There is no test suite. At minimum run `python -m py_compile solmate*.py`, then test against a
  real SolMate (see the update procedure below).
* Work in a branch and open a pull request against `main`; `main` is protected.

### Versioning and Changelog

For a release:

* Bump `version` in `solmate_main.py` (semantic versioning).
* Add an entry to `changelog.md` with the date (`## [x.y.z] YYYY.MM.DD`). Explain **what** changed
  and **why** it matters for users.
* Breaking changes (config keys, behavior that needs user action) also go into `breaking.md`.
* Update the README if supported versions or features change.
* After merging, create a GitHub release with the tag `vx.y.z` on `main`.

## Updating an AppDaemon Installation

This is how an agent with shell access to the AppDaemon host (for example via SSH) can update `esham`
without manual file copying. Always ask the user before touching a running installation.

The manual way is described in [docs/upgrade.md](./docs/upgrade.md). The agent does the same steps,
but scripted and with a backup.

### 1. Find the Target

* **AppDaemon container:** the host directory mounted as `/conf` (see `docker inspect <container>`),
  `esham` lives in `<conf>/apps/solmate/` (the folder may be named differently, check `apps.yaml`).
* **AppDaemon HA add-on:** `addon_configs/<id>_appdaemon/apps/solmate/` (internal path `/config`).
  Needs the SSH or Samba add-on for file access.
* Check `apps.yaml` for all `solmate_appdaemon_N` apps. More than one means multiple SolMates.

### 2. Back Up

Create an archive of the whole `esham` app folder before changing anything, for example
`tar czf solmate-backup-v<old version>-<date>.tar.gz -C <conf>/apps solmate`. Keep it next to the
folder or somewhere the user agrees on.

### 3. Copy the Code

* Copy the `solmate*.py` files and `requirements.txt` from the repository (checked out at the release
  tag or the branch to test) into the app folder, for example with `tar` piped over SSH or `rsync`.
* **Never overwrite** `.env*`, log files (`*.log`) or `my_packages/`.
* **Additional starters** (`solmate_appdaemon_1.py`, ...) are user copies of `solmate_appdaemon_0.py`
  with their own class name and `env_name_appendix`. They are not in the repository. If
  `solmate_appdaemon_0.py` changed, apply the same change to them and keep their own names and
  settings. The same applies if the user changed settings like `autostart` or `monitor_app` in
  `solmate_appdaemon_0.py`: compare before overwriting.
* Keep the file owner of the existing files (the user the AppDaemon container runs as, often UID 1000).
* Remove `__pycache__/` in the app folder.

### 4. Restart and Verify

* AppDaemon only reloads changed apps automatically when `production_mode` is off. With
  `production_mode: True`, and in general because `esham` runs as a separate process, **restart
  AppDaemon** (container restart or add-on restart).
* Check the AppDaemon log: the app starts (`AppDaemon: starting solmate_0`) and the `esham` log shows
  a working SolMate and MQTT connection, without tracebacks. The version is not logged, check
  `version` in the deployed `solmate_main.py` if needed.
* If the HA toggle is used, switch `input_boolean.solmate_appdaemon_0` off and on again. The log must
  show a clean stop and start.
* In HA, the SolMate entities must update again.

### 5. Roll Back

If something fails, stop AppDaemon, extract the backup archive over the app folder, and start
AppDaemon again.
