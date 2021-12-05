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


from log import LOGGER
from const import (
    STATE,
    TOPIC,
    PAYLOAD,
    SENSOR,
)

LOG_PREFIX = "[HomeAgent]"
###############################################################
class HomeAgent:
    """Class to collect and report endpoint data"""

    ###########################################################
    def __init__(self, config, sensors=None):
        """Init class"""
        self._config = config
        self._connector = None
        self._ha_connected = False
        self._modules = {}
        self._callback = {}
        self._services = {}
        self._last_sensors = {}
        self.platform_class = None
        self.device = {}
        self.states = {}
        self.attribs = {}
        self.icons = {}
        self.sensors = sensors
        if self.sensors is None:
            self.sensors = self._config.sensors.get("publish")

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

        _connected = threading.Event()
        _connected.clear()

        client_id = f"homeagent_{self._config.hostname}_{int(time.time())}"
        self._connector = _mod_class(self._config, _connected, client_id)

        self._connector.message_callback(self.message_receive)
        for topic in self._config.subscriptions:
            LOGGER.info("%s Connector subscribe: %s", LOG_PREFIX, topic)
            self._connector.subscribe_to(topic)

        self._connector.start()

        if not _connected.wait(10):
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
        self._ha_connected = True

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
            LOGGER.debug(
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

            except Exception as err:
                LOGGER.error(
                    "###########################################################"
                )
                LOGGER.error("%s Failed to load module %s. %s", LOG_PREFIX, _name, err)
                LOGGER.error(traceback.format_exc())
                LOGGER.error(
                    "###########################################################"
                )

    ###########################################################
    def start(self):
        """Init system info and sensors"""

        LOGGER.debug("%s Running startup tasks", LOG_PREFIX)
        self.start_time = time.time()
        self.get_sysinfo()
        self.get_identifier()
        self._publish_device()
        self.modules()
        self._add_sensor_prefixes()
        self._setup_sensors()
        self._setup_device_tracker()
        self._publish_online()

        if self._ha_connected:
            self.update_sensors(True)
            self.update_device_tracker()

    ###########################################################
    def stop(self):
        """Send offline message and stop connector"""

        LOGGER.info("%s Stopping", LOG_PREFIX)
        for module in self._modules:
            if hasattr(self._modules[module], "stop"):
                self._modules[module].stop()

        self._publish_online("offline")
        self._connector.stop()
        self._ha_connected = False

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
                LOGGER.debug(
                    "%s prefix_class: %s for sensor: %s", LOG_PREFIX, item, sensor
                )
                value = self._config.sensors.prefix_class.get(item[0])
                self._config.sensors.sensor_class[sensor] = value

            # Add sensor icon data
            item = [prefix for prefix in prefix_icon if prefix in sensor]
            if item:
                LOGGER.debug(
                    "%s prefix_icon: %s for sensor: %s", LOG_PREFIX, item, sensor
                )
                value = self._config.sensors.prefix_icons.get(item[0])
                self._config.sensors.icons[sensor] = value

    ###########################################################
    def conn_ping(self):
        """Ping Home Assistant connector"""
        self._connector.ping("homeassistant/ping")

    ###########################################################
    def get_identifier(self):
        """Get a unique id for this device"""

        _items = ["serial", "mac_address", "ip_address"]
        _id = None
        while _id is None and len(_items) > 0:
            _key = _items.pop(0)
            _id = self.states.get(_key)
            if "Serial" in _id:
                _id = None

        LOGGER.info("%s Device identifier: %s", LOG_PREFIX, _id)
        self._config.identifier = _id

    ###########################################################
    def metrics(self):
        """Run tasks to publish metrics"""

        LOGGER.debug("%s Running device metrics collection", LOG_PREFIX)
        self.get_sysinfo()
        if self._ha_connected:
            self.update_sensors()

    ###########################################################
    def modules(self):
        """Run tasks to publish metrics"""

        LOGGER.debug("%s Running modules", LOG_PREFIX)
        for slug in self._modules:
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
        self._publish_online()
        if self._ha_connected:
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
    def message_send(self, _data):
        """Send message to Home Assistant using connector"""

        # LOGGER.debug("%s message: %s", LOG_PREFIX, _data.get(TOPIC))
        _topic = _data.get(TOPIC)
        _payload = _data.get(PAYLOAD)
        if _topic is not None and _payload is not None:
            self._connector.publish(_topic, _payload)

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

        if command == "event":
            if payload.lower() in ["birth", "online", "pong"]:
                if not self._ha_connected:
                    LOGGER.info("%s Home Assistant connection is online", LOG_PREFIX)
                    self._ha_connected = True
                    self.start()

            elif payload.lower() in ["will", "offline"]:
                LOGGER.warning("%s Home Assistant connection offline", LOG_PREFIX)
                self._ha_connected = False

        elif command == "set":
            sensor = _data.get(TOPIC, "").split("/")[-2].split("_", 1)[1]
            LOGGER.debug("%s sensor: %s set state: %s", LOG_PREFIX, sensor, payload)
            if sensor in self._callback:
                _func = self._callback.get(sensor)
                _state = _func(sensor, payload)
                self.states[sensor] = _state
                self.update_sensors(True, [sensor])

        elif command in self._services:
            LOGGER.info("%s cmd calling service %s()", LOG_PREFIX, command)
            try:
                self._services[command](json.loads(payload))
            except json.JSONDecodeError as err:
                LOGGER.error("%s Failed to decode command payload. %s", LOG_PREFIX, err)
            except Exception as err:
                LOGGER.error("%s Module command error. %s", LOG_PREFIX, err)

    ###########################################################
    def _publish_online(self, _state="online"):
        """Publish online status"""

        self.message_send(
            {
                TOPIC: f"{self._config.prefix.device}/{self._config.hostname}/availability",
                PAYLOAD: _state,
            }
        )

    ###########################################################
    def _publish_device(self):
        """Publish device config"""

        LOGGER.debug("%s publish_device %s", LOG_PREFIX, self._config.hostname)
        self.device = setup_device(self._config, self.states)
        _data = setup_sensor(
            self._config,
            "trigger_turn_on",
            "device_automation",
        )
        _data[PAYLOAD].update(self.device)
        self.message_send(_data)

    ###########################################################
    def _setup_module_services(self, _module):
        """Configure services from loaded module"""

        _services = self._modules[_module].services
        if not _services:
            return

        for _service, items in tuple(_services.items()):
            LOGGER.info(
                "%s Setup service %s for module %s", LOG_PREFIX, _service, _module
            )
            self._services[_service] = getattr(self._modules[_module], _service)
            topic = f"{self._config.prefix.device}/{self._config.hostname}/{_service}"
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
            self.message_send(_data)
            time.sleep(0.033)

            _data[PAYLOAD].update({"name": _name})
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
                if _attrib:
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
                "name": f"{self._config.hostname}_location",
                "source_type": "router",
            }
        )
        self.message_send(_data)

        _data[PAYLOAD].update({"name": self._config.host.friendly_name})
        self.message_send(_data)

    ###########################################################
    def update_device_tracker(self):
        """Publish device_tracker to MQTT broker"""

        unique_id = f"{self.states['hostname']}_location"
        LOGGER.debug("%s Running device_tracker.%s update", LOG_PREFIX, unique_id)

        location = "not_home"
        for _loc, _net in self._config.device_tracker.items():

            network = ipaddress.ip_network(_net)
            if network.version != 4:
                ip = self.states["ip6_address"]
            else:
                ip = self.states["ip_address"]

            addr = ipaddress.ip_address(ip)
            if addr in network:
                LOGGER.debug(
                    "%s ip: %s net: %s location: %s", LOG_PREFIX, addr, network, _loc
                )
                location = self._config.locations.get(_loc)

        _topic = f"{self._config.prefix.discover}/device_tracker/{unique_id}/state"
        self.message_send({TOPIC: _topic, PAYLOAD: f"{location}"})

        payload = {
            "source_type": "router",
            "hostname": self._config.hostname,
        }

        mac_address = self.states.get("mac_address")
        if mac_address:
            payload["mac_address"] = mac_address

        ip_address = self.states.get("ip_address")
        if ip_address:
            payload["ip_address"] = ip_address

        battery_level = int(self.states.get("battery_percent", 0))
        if battery_level > 0:
            payload["battery_level"] = str(battery_level)

        if len(payload) > 0:
            _topic = f"{self._config.prefix.discover}/device_tracker/{unique_id}/attrib"
            self.message_send({TOPIC: _topic, PAYLOAD: payload})


#######################################################
def setup_device(_config, _sysinfo):
    """Return dict with device data"""

    return {
        "device": {
            "name": _config.host.friendly_name,
            "identifiers": _config.identifer,
            "connections": [["mac", _sysinfo.get("mac_address")]],
            "manufacturer": _sysinfo.get("manufacturer"),
            "model": _sysinfo.get("model"),
            "sw_version": _sysinfo.get("platform_release"),
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

    topic = f"homeassistant/{sensor_type}/{unique_id}"
    config_topic = f"{topic}/config"

    payload = {
        "~": topic,
        "name": unique_id,
        "unique_id": unique_id,
        "state_topic": "~/state",
        "device": {"identifiers": _config.identifier},
    }

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
