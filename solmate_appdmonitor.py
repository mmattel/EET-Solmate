import multiprocessing

# global variables for that module
# note that 'iself' is an artifice to manage appdeamon calls easily, see the callback
# note that platform must include a trailing dot
iself = None
solmates_to_monitor = {}
platform = 'input_boolean.'
on = 'on'
off = 'off'

def start_monitoring(self, sn, app_name):
	# called when initialize() is initiated
	global iself
	global solmates_to_monitor
	global platform	

	if iself is None:
		# only needs to be defined once
		iself = self

	# we name the entity for HA by the name of the python script (sn)
	# which it is also the name of the process to query
	# but the app name itself to start is defined in apps.yml
	# script name != app name (usually)
	# because each script needs it own .env, we also have an own app name

	# add key/value if not exists
	solmates_to_monitor[sn] = app_name

	entityID = platform + sn

	if not check_if_entity_exists(entityID):
		# check if the entity exists in HA and log a note if not
		message  = 'To monitor this Solmate, you need to add an integration in HA manually. '
		message += 'Settings -> Devices & Services -> Helpers -> Create Helper. '
		message += 'Select the "Toggle (Schalter)" helper and name it: ' + sn + ' '
		message += 'For the icon, select mdi:script-text-play-outline or any other you like. '
		message += 'When done, restart Appdaemon. You can now stop and restart esham via HA/Appdaemon.'
		iself.log(message)
		return

	iself.log('Entity: ' + entityID + ' found in HA, start listening')

	# set entity state in HA for the app to be running
	set_state_for_ha(entityID, on)

	# listen to entity state changes
	listen_to_ha(entityID)

def stop_monitoring(sn):
	# called when terminate() is initiated
	global iself
	global platform
	entityID = platform + sn

	# if exists, try to set the switch in HA to off
	# note that this curently does not work because
	# AD disconnects from HA before running terminate()
	# we keep it, it may get fixed or I find another practicable solution
	entityID = platform + sn
	if check_if_entity_exists(entityID):
		set_state_for_ha(entityID, off)

def check_if_entity_exists(entityID):
	# check if the entity exists in HA
	global iself
	return iself.entity_exists(entityID)

def set_state_for_ha(entityID, st):
	# set the state of the entity in HA to
	iself.set_state(entityID, state=st)

def listen_to_ha(entityID):
	# create a listener for the entity
	# all entities have the same listener
	global iself
	iself.listen_state(entity_cb, entityID)

def entity_cb(entity, attribute, old, new, kwargs):
	# callback for entity changes
	# the returned entity is the one we take care on
	# note that an entity returned was fomerly added by the listener
	global iself
	global solmates_to_monitor
	global platform

	#iself.log(f'{entity} {attribute} {old} {new}')
	sn = entity.replace(platform, '')
	if 'off' in new:
		terminate_app(sn)
	else:
		# we know that 'solmates_to_monitor' is proper populated and has unique keys
		# the sn's value defines the app name to start
		start_app(sn, solmates_to_monitor[sn])

def terminate_app(sn):
	# terminate the app if running
	global iself
	p, found = get_running_state(sn)
	if found:
		p.terminate()
		iself.log(sn + ' has been terminated by request via HA')

def start_app(sn, app_name):
	# start the app if not running
	global iself
	p, found = get_running_state(sn)
	if not found:
		iself.restart_app(app_name)
		iself.log(sn + ' has been started by request via HA')

def get_running_state(sn):
	# check if this app is running
	for p in multiprocessing.active_children():
		if sn in p.name:
			return p, True
	else:
		return False, False
