import multiprocessing

# global variables for that module

# though the AD docs state custom args/kwargs can be used in callbacks, you need to read the
# docs carefully. they only provide exampes where key=string. using as value an object like self,
# this currently does not work and imho seems a bug to me.
# therefore global envvars needs to be defined so the callback can use it

# 'iself' is an artifice to manage appdeamon calls easily, like in entity callback or logs
iself = None

# note that platform MUST include a trailing dot
platform = 'input_boolean.'

# list of solmates that are managed
solmates_to_monitor = {}

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

	if not check_if_entity_exists(iself, entityID):
		# check if the entity exists in HA and log a note if not
		message  = 'To monitor this Solmate, you need to add an integration in HA manually. '
		message += 'Settings -> Devices & Services -> Helpers -> Create Helper. '
		message += 'Select the "Toggle (Schalter)" helper and name it: ' + sn + ' '
		message += 'For the icon, select mdi:script-text-play-outline or any other you like. '
		message += 'When done, restart Appdaemon. You can now stop and restart esham via HA/Appdaemon.'
		iself.log(message)
		return

	# set entity state in HA for the app (p is the handle not used here, found is bool)
	p, found = get_running_state(sn)
	state = 'on' if found else 'off'
	set_entity_state(iself, entityID, state)

	iself.log('AppDaemon: Entity: ' + entityID + ' found in HA, start listening')

	# listen to entity state changes
	listen_entity(iself, entityID)

def stop_monitoring(iself, sn):
	# called when terminate() is initiated
	global platform

	entityID = platform + sn

	# if exists, try to set the switch in HA to off
	# note that this curently does not work because
	# AD disconnects from HA before running terminate()
	# we keep it, it may get fixed or I find another practicable solution
	entityID = platform + sn
	if check_if_entity_exists(iself, entityID):
		set_entity_state(iself, entityID, 'off')

def check_if_entity_exists(iself, entityID):
	# check if the entity exists in HA
	return iself.entity_exists(entityID)

def set_entity_state(iself, entityID, st):
	# set the state of the entity in HA

	iself.set_state(entityID, state = st)

def listen_entity(iself, entityID):
	# create a listener for the event and return the handle
	# all entities call the same listener code
	# when kwargs are working with AD, we can add iself as custom argument
	iself.listen_state(entity_cb, entityID)

def entity_cb(entity, attribute, old, new, kwargs):
	# callback for entity changes
	# the returned entity is the one we take care on
	# note that an entity returned was fomerly added by the listener
	global iself
	global solmates_to_monitor
	global platform

	sn = entity.replace(platform, '')

	if 'off' in new:
		terminate_app(iself, sn)
	else:
		# we know that 'solmates_to_monitor' is proper populated and has unique keys
		# the sn's value defines the app name to start
		start_app(iself, sn, solmates_to_monitor[sn])

def terminate_app(iself, sn):
	# terminate the app if running
	p, found = get_running_state(sn)
	if found:
		p.terminate()
		iself.log('AppDaemon: ' + sn + ' has been terminated by request via HA')

def start_app(iself, sn, app_name):
	# start the app if not running
	p, found = get_running_state(sn)
	if not found:
		iself.restart_app(app_name)
		iself.log('AppDaemon: ' + sn + ' has been started by request via HA')

def get_running_state(sn):
	# check if this app is running
	for p in multiprocessing.active_children():
		if sn in p.name:
			return p, True
	else:
		return False, False
