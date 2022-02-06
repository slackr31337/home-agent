"""Home Agent class for endpoint functions"""

import os
import sys
import time
import traceback
import threading
import importlib
import pathlib
import glob
import json
import ipaddress


from utilities.log import LOGGER
from utilities.util import calc_elasped
from config import ONLINE_ATTRIB
from const import (
    ATTRIBS,
    STATE,
    TOPIC,
    PAYLOAD,
    SENSOR,
    START_TIME,
    NAME,
    LAST,
    PING,
    PONG,
    EVENT,
    SET,
    BIRTH,
    WILL,
    ONLINE,
    OFFLINE,
    PUBLISH,
    SERIAL,
    IP_ADDRESS,
    MAC_ADDRESS,
    DEVICE,
    STATE_TOPIC,
    AVAILABILITY_TOPIC,
    ROUTER,
    HOSTNAME,
    BATTERY_PERCENT,
    BATTERY_LEVEL,
    BINARY_SENSOR,
    SOURCE_TYPE,
    IDENTIFIERS,
    CONNECTIONS,
    MANUFACTURER,
    MODEL,
    UNIQUE_ID,
    STATUS,
    GET,
)

LOG_PREFIX = "[HomeAgent]"
###############################################################
class HomeAgent:  # pylint:disable=too-many-instance-attributes
    """Class to collect and report endpoint data"""

    ###########################################################
    def __init__(self, config, running, sched, sensors=None):
        """Init class"""
        self._connected_event = threading.Event()
        self._config = config
        self._running = running
        self._sched = sched
        self._connector = None
        self._ha_connected = False
        self.states = {}
        self._stats = {LAST: {}}
        self._modules = {}
        self._callback = {}
        self._services = {}
        self._last_sensors = {}
        self.platform_class = None
        self.device = {}
        self.attribs = {}
        self.icons = {}
        self.sensors = sensors
        if self.sensors is None:
            self.sensors = self._config.sensors.get(PUBLISH)

        self._os_module()
        self._connector_module()
        self._load_modules()

    ###########################################################
    def _os_module(self):
        """Load OS module"""

        mod_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "os")
        sys.path.append(mod_dir)

        LOGGER.info(
            "%s Loading OS module: %s",
            LOG_PREFIX,
            self._config.platform,
        )
        if not os.path.exists(f"{mod_dir}/{self._config.platform}.py"):
            LOGGER.error(
                "%s OS module [%s] not found in %s",
                LOG_PREFIX,
                self._config.platform,
                mod_dir,
            )
            raise Exception("OS module not found")

        os_module = os.path.join(mod_dir, f"{self._config.platform}.py")

        _name = pathlib.Path(os_module).stem
        _module = importlib.import_module(_name)
        _mod_class = getattr(_module, "AgentPlatform")
        self.platform_class = _mod_class()

    ###########################################################
    def _connector_module(self):
        """Load connector module"""

        mod_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "connector")
        sys.path.append(mod_dir)

        LOGGER.info(
            "%s Loading connector module: %s", LOG_PREFIX, self._config.connector
        )
        conn_module = os.path.join(mod_dir, f"{self._config.connector}.py")

        _name = pathlib.Path(conn_module).stem
        _module = importlib.import_module(_name)
        _mod_class = getattr(_module, "Connector")

        self._connected_event.clear()
        client_id = f"homeagent_{self._config.hostname}_{int(time.time())}"
        self._connector = _mod_class(
            self._config, self._connected_event, self._running, client_id
        )

        self._connector.message_callback(self.message_receive)
        self._connector.set_will(f"{self._config.device.topic}/status", OFFLINE)
        for topic in self._config.subscriptions:
            LOGGER.info("%s Connector subscribe: %s", LOG_PREFIX, topic)
            self._connector.subscribe_to(topic)

        self._connector.start()

        if not self._connected_event.wait(15):
            LOGGER.error(
                "%s Connector timeout. Connected: %s",
                LOG_PREFIX,
                self._connector.connected(),
            )
            raise Exception(
                "Failed to get connection to Home Assistant. Check auth password or token."
            )

        LOGGER.info(
            "%s Connector is connected: %s", LOG_PREFIX, self._connector.connected()
        )
        self._ha_connected = self._connector.connected()

    ###########################################################
    def _load_modules(self):
        """Load module from directory modules"""

        mod_dir = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            f"modules/{self._config.platform}",
        )
        sys.path.append(mod_dir)

        LOGGER.debug("%s Loading modules from %s", LOG_PREFIX, mod_dir)
        _mods = glob.glob(os.path.join(mod_dir, "*.py"))

        for _mod in _mods:
            _name = pathlib.Path(_mod).stem
            LOGGER.info(
                "%s Import module: %s-%s", LOG_PREFIX, self._config.platform, _name
            )

            _module = importlib.import_module(_name)
            if not hasattr(_module, "AgentModule"):
                LOGGER.error(
                    "%s Failed to load module %s. AgentModule class not found",
                    LOG_PREFIX,
                    _module,
                )
                continue

            _mod_class = getattr(_module, "AgentModule")

            try:
                _class = _mod_class()
                LOGGER.info("%s [%s] Loaded %s", LOG_PREFIX, _class.slug, _class.name)
                self._modules[_class.slug] = _class
                self._setup_module_sensors(_class.slug)
                self._setup_module_services(_class.slug)

            except Exception as err:  # pylint: disable=broad-except
                LOGGER.error("%s Failed to load module %s. %s", LOG_PREFIX, _name, err)
                LOGGER.debug(traceback.format_exc())

    ###########################################################
    def stop(self):
        """Send offline message and stop connector"""

        LOGGER.info("%s Stopping", LOG_PREFIX)
        self._publish_online(OFFLINE)
        for module in self._modules:  # pylint: disable=consider-using-dict-items
            if hasattr(self._modules[module], "stop"):
                self._modules[module].stop()

        LOGGER.info("%s Disconnecting", LOG_PREFIX)
        self._connected_event.clear()
        self._connector.stop()
        self._ha_connected = False
        LOGGER.info("%s Exit", LOG_PREFIX)

    ###########################################################
    def start(self):
        """Init system info and sensors"""

        LOGGER.debug("%s Running startup tasks", LOG_PREFIX)
        start = int(time.time())
        self._stats[START_TIME] = start
        self._load_state()
        self.get_sysinfo()
        self.get_identifiers()
        self.get_connections()
        self._publish_device()
        self.modules()
        self._add_sensor_prefixes()
        self._setup_sensors()
        self._setup_device_tracker()

        elasped = calc_elasped(start)
        LOGGER.info("%s Startup finished in %s", LOG_PREFIX, elasped)

    ###########################################################
    def conn_ping(self):
        """Ping Home Assistant connector"""
        last_pong = self._stats[LAST].get(PONG, 0)
        last_ping = self._stats[LAST].get(PING, 0)
        delta = int(last_ping - last_pong)

        LOGGER.debug("%s [Ping] delta: %s", LOG_PREFIX, delta)
        if last_ping != 0 and delta > 300:
            elasped = calc_elasped(last_ping)
            LOGGER.warning(
                "%s Last ping response was %s ago. Restarting home-agent",
                LOG_PREFIX,
                elasped,
            )
            self.stop()
            time.sleep(5)
            self.start()

        if self._ha_connected:
            self._connector.ping("homeassistant/status")
            self._stats[LAST][PING] = int(time.time())

        else:
            LOGGER.error("%s HA is disconnected", LOG_PREFIX)

    ###########################################################
    def _add_sensor_prefixes(self):
        """Add sensors that match prfixes"""
        prefix_sensors = self._config.sensors.get("prefix", [])
        prefix_class = tuple(self._config.sensors.prefix_class.keys())
        prefix_icon = tuple(self._config.sensors.prefix_icons.keys())

        sensors = tuple(self.states.keys())
        for sensor in sensors:
            item = [prefix for prefix in prefix_sensors if prefix in sensor]
            if not item:
                continue

            # Add sensor to metrics collection
            self.sensors[sensor] = {}

            # Add sensor device class data
            item = [prefix for prefix in prefix_class if prefix in sensor]
            if item:
                value = self._config.sensors.prefix_class.get(item[0])
                self._config.sensors.sensor_class[sensor] = value
                LOGGER.debug(
                    "%s prefix_class: %s for sensor: %s %s",
                    LOG_PREFIX,
                    item,
                    sensor,
                    value,
                )

            # Add sensor icon data
            item = [prefix for prefix in prefix_icon if prefix in sensor]
            if item:
                LOGGER.debug(
                    "%s prefix_icon: %s for sensor: %s", LOG_PREFIX, item, sensor
                )
                value = self._config.sensors.prefix_icons.get(item[0])
                self._config.sensors.icons[sensor] = value

    ###########################################################
    def get_identifiers(self):
        """Get a unique identifier for this device"""

        items = [SERIAL, MAC_ADDRESS, IP_ADDRESS]
        _id = None
        while _id is None and len(items) > 0:
            _key = items.pop(0)
            _id = self.states.get(_key)
            if "Serial" in _id or "O.E.M." in _id:
                _id = None

        self._config.device.identifiers = _id

        LOGGER.info("%s Device identifier: %s", LOG_PREFIX, _id)

    ###########################################################
    def get_connections(self):
        """Get connection identifiers for this device"""

        _conn = [[IP_ADDRESS, self.states.get(IP_ADDRESS)]]
        for _value in self.states.get("mac_addresses"):
            if _value:
                _conn.append(["mac", _value])

        self._config.device.connections = _conn
        LOGGER.info("%s Device connections: %s", LOG_PREFIX, _conn)

    ###########################################################
    def metrics(self):
        """Run tasks to publish metrics"""

        LOGGER.debug("%s Running device metrics collection", LOG_PREFIX)
        self._stats[LAST]["metrics"] = int(time.time())
        self.get_sysinfo()
        if self._ha_connected:
            self.update_sensors()

    ###########################################################
    def modules(self):
        """Run tasks to publish metrics"""
        if not self._ha_connected:
            return

        LOGGER.debug("%s Running modules", LOG_PREFIX)
        for slug in self._modules:  # pylint: disable=consider-using-dict-items
            _sensors = self._modules[slug].sensors
            LOGGER.debug("%s module %s sensors %s", LOG_PREFIX, slug, _sensors)
            for _sensor in _sensors:
                _value, _attrib = self._modules[slug].get(_sensor)
                self.states[_sensor] = _value
                self.attribs[_sensor] = _attrib

    ###########################################################
    def events(self):
        """Run tasks to publish events"""

        LOGGER.debug("%s Running events", LOG_PREFIX)
        self._stats[LAST]["events"] = int(time.time())
        self._save_state()
        if self._ha_connected:
            self._publish_online()
            self.update_sensors(True)
            self.update_device_tracker()

    ###########################################################
    def get_sysinfo(self):
        """Collect system info"""

        self.platform_class.update()
        states, attribs = self.platform_class.state()
        self.states.update(states)
        self.attribs.update(attribs)

    ###########################################################
    def _save_state(self):
        """Write state dict to file"""
        _file = f"{self._config.dir}/state.json"
        LOGGER.debug("%s Saving states to %s", LOG_PREFIX, _file)
        with open(_file, "w", encoding="utf-8") as _states:
            _state = {
                STATE: self.states.copy(),
                ATTRIBS: self.attribs.copy(),
                DEVICE: self.device.copy(),
            }
            if "screen_capture" in _state[STATE]:
                _state[STATE].pop("screen_capture")
            _states.write(json.dumps(_state, default=str, indent=4))

    ###########################################################
    def _load_state(self):
        """Write state dict to file"""
        _file = f"{self._config.dir}/state.json"
        if not os.path.exists(_file):
            return

        LOGGER.debug("%s Loading states from %s", LOG_PREFIX, _file)
        with open(_file, "r", encoding="utf-8") as _states:
            _data = _states.read()

        try:
            _state = json.loads(_data)
            self.states = _state.get(STATE)
            self.attribs = _state.get(ATTRIBS)

        except json.JSONDecodeError as err:
            LOGGER.error("%s Failed to load states from json", LOG_PREFIX)
            LOGGER.error(err)

    ###########################################################
    def message_send(self, _data):
        """Send message to Home Assistant using connector"""
        if not self._ha_connected:
            return False

        # LOGGER.debug("%s message: %s", LOG_PREFIX, _data.get(TOPIC))
        _topic = _data.get(TOPIC)
        _payload = _data.get(PAYLOAD)
        if _topic is None or _payload is None:
            LOGGER.error("%s payload or topic missing", LOG_PREFIX)
            return False

        return self._connector.publish(_topic, _payload)

    ###########################################################
    def message_receive(self, _data):
        """Receive message from Home Assistant using connector"""

        LOGGER.debug("%s Message received. %s", LOG_PREFIX, _data)
        self.process_cmd(_data)

    ###########################################################
    def process_cmd(self, _data):
        """Process message from Home Assistant"""

        topic = _data.get(TOPIC, "").split("/")
        command = topic[-1]
        payload = _data.get(PAYLOAD)
        LOGGER.debug(
            "%s %s.%s payload: %s",
            LOG_PREFIX,
            topic,
            command,
            payload,
        )
        now = int(time.time())
        if command == EVENT or command == STATUS:
            LOGGER.debug("%s Event: %s", LOG_PREFIX, command)
            self._stats[LAST][EVENT] = now

            event_type = payload.lower()
            if event_type in [BIRTH, ONLINE, PONG]:
                self._stats[LAST][event_type] = now
                if not self._ha_connected:
                    LOGGER.info("%s Home Assistant connection is online", LOG_PREFIX)
                    self._ha_connected = True
                    self.start()

            elif event_type in [WILL, OFFLINE]:
                self._stats[LAST][event_type] = now
                LOGGER.warning("%s Home Assistant connection offline", LOG_PREFIX)
                self._ha_connected = False

            elif event_type == GET:
                self._stats[LAST][event_type] = now
                LOGGER.debug("%s Get %s", LOG_PREFIX, command)
                self.message_send(
                    {
                        TOPIC: f"{self._config.device.topic}/status",
                        PAYLOAD: self._stats,
                    }
                )

        elif command == SET:
            sensor = _data.get(TOPIC, "").split("/")[-2].split("_", 1)[1]
            LOGGER.info("%s cmd set: %s state: %s", LOG_PREFIX, sensor, payload)
            if sensor in self._callback:
                _func = self._callback.get(sensor)
                _state = _func(sensor, payload)
                self.states[sensor] = _state
                self.update_sensors(True, [sensor])

        elif command == GET:
            _type = payload.lower()
            LOGGER.info("%s cmd get: %s", LOG_PREFIX, _type)

        elif command in self._services:
            LOGGER.info("%s cmd calling service %s()", LOG_PREFIX, command)
            try:
                self._services[command](json.loads(payload))

            except json.JSONDecodeError as err:
                LOGGER.error("%s Failed to decode command payload. %s", LOG_PREFIX, err)
                LOGGER.error("%s payload: %s", LOG_PREFIX, payload)

            except Exception as err:  # pylint: disable=broad-except
                LOGGER.error("%s Module command error. %s", LOG_PREFIX, err)

    ###########################################################
    def _publish_online(self, _state="online"):
        """Publish online status"""

        if not self.message_send(
            {
                TOPIC: f"{self._config.device.topic}/status",
                PAYLOAD: _state,
            }
        ):
            self._ha_connected = False

    ###########################################################
    def _publish_device(self):
        """Publish device config"""

        LOGGER.debug("%s publish_device %s", LOG_PREFIX, self._config.hostname)
        self.device = setup_device(self._config, self.states)

        _data = setup_sensor(
            self._config,
            "Online",
            BINARY_SENSOR,
            ONLINE_ATTRIB,
        )
        _data[PAYLOAD].update(self.device)
        _data[PAYLOAD].update(
            {
                "~": self._config.device.topic,
                STATE_TOPIC: self._config.device.availability,
            }
        )

        self.message_send(_data)
        _data[PAYLOAD][NAME] = "Online"
        self.message_send(_data)
        self._publish_online()

    ###########################################################
    def _setup_module_services(self, _module):
        """Configure services from loaded module"""

        _services = self._modules[_module].services
        if not _services:
            return

        for _service, items in tuple(_services.items()):
            LOGGER.info(
                "%s Setup service %s for module %s (%s)",
                LOG_PREFIX,
                _service,
                _module,
                items,
            )
            self._services[_service] = getattr(self._modules[_module], _service)
            topic = f"{self._config.device.topic}/{_service}"
            self._connector.subscribe_to(topic)

    ###########################################################
    def _setup_module_sensors(self, _module):
        """Configure sensors from loaded module"""

        _sensors = self._modules[_module].sensors
        if not _sensors:
            return

        _sensor_types = self._modules[_module].sensor_types
        if _sensor_types:
            self._config.sensors.type.update(_sensor_types)

        _sensor_attribs = self._modules[_module].sensor_attribs
        if _sensor_attribs:
            self._config.sensors.attrib.update(_sensor_attribs)

        _sensor_icons = self._modules[_module].sensor_icons
        if _sensor_icons:
            self._config.sensors.icons.update(_sensor_icons)

        _sensors_set = self._modules[_module].sensors_set
        for _sensor in _sensors:
            LOGGER.info(
                "%s Setup sensor %s for module %s", LOG_PREFIX, _sensor, _module
            )
            self.sensors[_sensor] = {}

            _attrib = self._modules[_module].attribs.get(_sensor)
            if _attrib:
                self._config.sensors.attrib[_sensor] = _attrib
                LOGGER.debug("%s %s: %s", LOG_PREFIX, _sensor, _attrib)

            if _sensor in _sensors_set and hasattr(self._modules[_module], "set"):
                LOGGER.info("%s Setup callback %s.set()", LOG_PREFIX, _sensor)
                self._callback[_sensor] = self._modules[_module].set

    ###########################################################
    def _setup_sensors(self):
        """Publish sensor config to MQTT broker"""

        for sensor in tuple(self.sensors.keys()):
            _state = self.states.get(sensor)
            if _state is None:
                continue

            _name = sensor.title().replace("_", " ")
            _data = setup_sensor(self._config, _name)

            self._connected_event.clear()
            if not self.message_send(_data):
                continue

            self._connected_event.wait(3)

            _data[PAYLOAD].update(
                {NAME: _name, AVAILABILITY_TOPIC: self._config.device.availability}
            )
            self.message_send(_data)

            _data[TOPIC] = _data[TOPIC].split("/config", 2)[0] + "/state"

            self.sensors[sensor] = _data

            if sensor in self._callback:
                _topic = _data[TOPIC].split("/state", 2)[0] + "/set"
                LOGGER.info("%s Connector subscribe: %s", LOG_PREFIX, _topic)
                self._connector.subscribe_to(_topic)

    ###########################################################
    def update_sensors(self, _send_nochange=False, _sensors=None):
        """Send sensor data to MQTT broker"""

        LOGGER.debug(
            "%s Running update state for %s sensors", LOG_PREFIX, len(self.sensors)
        )
        if _sensors is None:
            _sensors = tuple(self.sensors.keys())

        for sensor in _sensors:
            _topic = self.sensors[sensor].get(TOPIC)
            _state = self.states.get(sensor)
            _last = self._last_sensors.get(sensor)

            if _state is None:
                LOGGER.debug("%s %s state is None", LOG_PREFIX, sensor)
                continue

            if isinstance(_state, list) and len(_state) == 1:
                _state = next(iter(_state), [])

            elif isinstance(_state, int) and int(_state) not in range(0, 10000):
                continue

            elif isinstance(_state, bytearray):
                _data = {TOPIC: _topic, PAYLOAD: _state}
                self.message_send(_data)
                continue

            # LOGGER.debug(
            #    "%s sensor[%s] state: %s %s", LOG_PREFIX, sensor, _state, type(_state)
            # )

            if _send_nochange or (_last is not None and _state != _last):
                LOGGER.debug(
                    "%s %s changed from [%s] to [%s]. Publishing new state",
                    LOG_PREFIX,
                    sensor,
                    _last,
                    _state,
                )

                if _state is not None:
                    _data = {TOPIC: _topic, PAYLOAD: {STATE: _state}}
                    self.message_send(_data)
                    self._last_sensors[sensor] = _state

                _attrib = self.attribs.get(sensor)
                if _attrib and _topic:
                    _topic = _topic.split("/state", 2)[0] + "/attrib"
                    self.message_send({TOPIC: _topic, PAYLOAD: _attrib})

        LOGGER.debug("%s Done updating sensors", LOG_PREFIX)

    ###########################################################
    def _setup_device_tracker(self):
        """Publish device_tracker to MQTT broker"""

        _data = setup_sensor(self._config, "location", "device_tracker")
        LOGGER.debug(
            "%s Setup device_tracker %s",
            LOG_PREFIX,
            f"{self._config.hostname}_location",
        )

        _data[PAYLOAD].update(
            {
                NAME: f"{self._config.hostname}_location",
                SOURCE_TYPE: ROUTER,
                AVAILABILITY_TOPIC: self._config.device.availability,
            }
        )
        if self.message_send(_data):
            _data[PAYLOAD].update({NAME: self._config.host.friendly_name})
            self.message_send(_data)

    ###########################################################
    def update_device_tracker(self):
        """Publish device_tracker to MQTT broker"""

        unique_id = f"{self.states[HOSTNAME]}_location"
        LOGGER.debug("%s Running device_tracker.%s update", LOG_PREFIX, unique_id)

        location = "not_home"
        for _loc, _net in self._config.device_tracker.items():

            network = ipaddress.ip_network(_net)
            if network.version != 4:
                ip_str = self.states["ip6_address"]
            else:
                ip_str = self.states[IP_ADDRESS]

            addr = ipaddress.ip_address(ip_str)
            if addr in network:
                LOGGER.debug(
                    "%s ip: %s net: %s location: %s", LOG_PREFIX, addr, network, _loc
                )
                location = self._config.locations.get(_loc)

        _topic = f"{self._config.prefix.discover}/device_tracker/{unique_id}/state"
        self.message_send({TOPIC: _topic, PAYLOAD: f"{location}"})

        payload = {
            SOURCE_TYPE: ROUTER,
            HOSTNAME: self._config.hostname,
        }

        mac_address = self.states.get(MAC_ADDRESS)
        if mac_address:
            payload[MAC_ADDRESS] = mac_address

        ip_address = self.states.get(IP_ADDRESS)
        if ip_address:
            payload[IP_ADDRESS] = ip_address

        battery_level = int(self.states.get(BATTERY_PERCENT, 0))
        if battery_level > 0:
            payload[BATTERY_LEVEL] = str(battery_level)

        if len(payload) > 0:
            _topic = f"{self._config.prefix.discover}/device_tracker/{unique_id}/attrib"
            self.message_send({TOPIC: _topic, PAYLOAD: payload})


#######################################################
def setup_device(_config, _states):
    """Return dict with device data"""

    if _config.device.identifiers is None:
        LOGGER.error("%s setup_device() Missing device identifier")
        raise Exception("Missing device identifier")

    return {
        DEVICE: {
            NAME: _config.host.friendly_name,
            IDENTIFIERS: _config.device.identifiers,
            CONNECTIONS: _config.device.connections,
            MANUFACTURER: _states.get(MANUFACTURER),
            MODEL: _states.get(MODEL),
            "sw_version": _states.get("firmware"),
        },
    }


########################################################
def setup_sensor(_config, sensor="Status", sensor_type=None, attribs=None):
    """Return dict with sensor config"""
    device_name = _config.hostname.lower().replace(" ", "_")
    sensor_name = sensor.lower().replace(" ", "_")
    unique_id = f"{device_name}_{sensor_name}"

    if not sensor_type:
        sensor_type = _config.sensors.type.get(sensor_name, SENSOR)

    LOGGER.debug(
        "%s setup_sensor[%s] (%s) type %s",
        LOG_PREFIX,
        sensor_name,
        sensor,
        sensor_type,
    )

    topic = f"{_config.prefix.discover}/{sensor_type}/{unique_id}"
    config_topic = f"{topic}/config"

    payload = {
        "~": topic,
        NAME: unique_id,
        UNIQUE_ID: unique_id,
        STATE_TOPIC: f"{topic}/state",
        DEVICE: {IDENTIFIERS: _config.device.identifiers},
    }

    if not attribs:
        attribs = _config.sensors.attrib.get(sensor_type)

    if attribs is not None:
        if isinstance(attribs, dict):
            for item, value in attribs.items():
                payload[item] = value

    _class = _config.sensors.sensor_class.get(sensor_name)
    if isinstance(_class, dict):
        payload.update(_class)

    _icon = _config.sensors.icons.get(sensor_name)
    if _icon:
        payload.update({"icon": f"mdi:{_icon}"})

    return {
        TOPIC: config_topic,
        PAYLOAD: payload,
    }
