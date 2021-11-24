"""Home Agent class for endpoint functions"""

import os
import sys
import time
import threading
import importlib
import pathlib
import glob
import json


from log import LOGGER
from ha_sensors import setup_sensor, setup_device
from config import (
    HOSTNAME,
    FRIENDLY_NAME,
    PLATFORM,
    MQTT_HA_PREFIX,
    MQTT_DEVICE_PREFIX,
    MQTT_SUBS,
    SENSOR_PREFIX_MAP,
    TYPE_MAP,
    ATTRIB_MAP,
    PUBLISH_SENSORS,
    IP_LOCATION_MAP,
    DEVICE_AVAILABILITY,
)

from const import (
    STATE,
    TOPIC,
    PAYLOAD,
)

LOG_PREFIX = "[HomeAgent]"
###############################################################
class HomeAgent:
    """Class to collect and report endpoint data"""

    ###########################################################
    def __init__(self, _args, sensors=None):
        """Init class"""
        self._args = _args
        self._connector = None
        self._ha_connected = False
        self._modules = {}
        self._callback = {}
        self._services = {}
        self.device = {}
        self._last_sensors = {}
        self._sensor_types = TYPE_MAP
        self._sensor_attribs = ATTRIB_MAP
        self.identifier = None
        self.sysinfo_class = None
        self.states = None
        self.sensors = sensors
        if self.sensors is None:
            self.sensors = PUBLISH_SENSORS

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
            PLATFORM,
        )
        if not os.path.exists(f"{mod_dir}/{PLATFORM}.py"):
            LOGGER.error(
                "%s OS module [%s] missing from %s", LOG_PREFIX, PLATFORM, mod_dir
            )
            raise "OS module missing"

        os_module = os.path.join(mod_dir, f"{PLATFORM}.py")

        _name = pathlib.Path(os_module).stem
        _module = importlib.import_module(_name)
        _mod_class = getattr(_module, "agent_platform")
        self.sysinfo_class = _mod_class()

    ###########################################################
    def _connector_module(self):
        """Load connector module"""

        mod_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "connector")
        sys.path.append(mod_dir)

        LOGGER.info("%s Loading connector module: %s", LOG_PREFIX, self._args.connector)
        conn_module = os.path.join(mod_dir, f"{self._args.connector}.py")

        _name = pathlib.Path(conn_module).stem
        _module = importlib.import_module(_name)
        _mod_class = getattr(_module, "connector")

        _connected = threading.Event()
        _connected.clear()
        client_id = f"homeagent_{HOSTNAME}_{int(time.time())}"
        self._connector = _mod_class(self._args, _connected, client_id)

        if self._connector.name == "mqtt":
            self._connector.message_callback(self.message_receive)
            for topic in MQTT_SUBS:
                LOGGER.info("%s Connector subscribe: %s", LOG_PREFIX, topic)
                self._connector.subscribe_to(topic)

        self._connector.start()

        if not _connected.wait(30):
            LOGGER.error(
                "%s Connector timeout. Connected: %s",
                LOG_PREFIX,
                self._connector.connected(),
            )
            return

        LOGGER.info(
            "%s Connector is connected: %s", LOG_PREFIX, self._connector.connected()
        )
        self._ha_connected = True

    ###########################################################
    def _load_modules(self):
        """Load module from directory modules"""

        mod_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "modules")
        sys.path.append(mod_dir)

        LOGGER.debug("%s Loading modules from %s", LOG_PREFIX, mod_dir)
        _mods = glob.glob(os.path.join(mod_dir, "*.py"))

        for _mod in _mods:
            _name = pathlib.Path(_mod).stem
            LOGGER.debug("%s Import module: %s", LOG_PREFIX, _name)

            _module = importlib.import_module(_name)
            _mod_class = getattr(_module, "agent_module")
            if PLATFORM not in _mod_class.platform:
                LOGGER.warning(
                    "%s [%s] Module does not support %s", LOG_PREFIX, _name, PLATFORM
                )
                continue

            try:
                _class = _mod_class()
                LOGGER.info("%s [%s] Loaded %s", LOG_PREFIX, _class.slug, _class.name)
                self._modules[_class.slug] = _class
                self._setup_module_sensors(_class.slug)
                self._setup_module_services(_class.slug)

            except Exception as err:
                LOGGER.error("%s Failed to load module %s. %s", LOG_PREFIX, _name, err)

    ###########################################################
    def start(self):
        """Init system info and sensors"""

        LOGGER.debug("%s Running startup tasks", LOG_PREFIX)
        self.start_time = time.time()
        self.get_sysinfo()
        self.get_identifier()
        self.modules()
        self._publish_device()
        self._add_sensor_prefixes()
        self._setup_sensors()
        self._setup_device_tracker()
        self._publish_online()
        time.sleep(2)
        self.update_sensors(True)
        self.update_device_tracker()

    ###########################################################
    def stop(self):
        """Send offline message and stop connector"""

        LOGGER.info("%s Stopping", LOG_PREFIX)
        self._publish_online("offline")
        self._connector.stop()
        self._ha_connected = False

    ###########################################################
    def _add_sensor_prefixes(self):
        """Add sensors that match prfixes"""

        for prefix in SENSOR_PREFIX_MAP:
            for sensor in self.states:
                if prefix in sensor:
                    self.sensors[sensor] = {}

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
        self.identifier = _id

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
                _value = self._modules[slug].get(_sensor)
                self.states[_sensor] = _value

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

        self.states = self.sysinfo_class.update()

    ###########################################################
    def message_send(self, _data):
        """Send message to Home Assistant using connector"""

        # LOGGER.debug("%s message: %s", LOG_PREFIX, _data.get(TOPIC))
        if self._connector.name == "mqtt":
            _topic = _data.get(TOPIC)
            _payload = _data.get(PAYLOAD)
            if _topic is not None and _payload is not None:
                self._connector.publish(_topic, _payload)
        else:
            LOGGER.error("%s No connection found.", LOG_PREFIX)

    ###########################################################
    def message_receive(self, _data):
        """Receive message from Home Assistant using connector"""

        LOGGER.debug("%s Message received. %s", LOG_PREFIX, _data)
        self.process_cmd(_data)

    ###########################################################
    def process_cmd(self, _data):
        """Process message from Home Assistant"""

        command = _data.get(TOPIC, "").split("/")[-1]
        payload = _data.get(PAYLOAD)
        LOGGER.info("%s command: %s payload: %s", LOG_PREFIX, command, payload)

        if command == "status":
            if "birth" in payload or "online" in payload:
                self._ha_connected = True
                self.start()

            elif "will" in payload or "offline" in payload:
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
            LOGGER.debug("%s calling service %s", LOG_PREFIX, command)
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
                TOPIC: f"{MQTT_DEVICE_PREFIX}/{HOSTNAME}/availability",
                PAYLOAD: _state,
            }
        )

    ###########################################################
    def _publish_device(self):
        """Publish device config"""

        LOGGER.debug("%s publish_device %s", LOG_PREFIX, HOSTNAME)
        self.device = setup_device(FRIENDLY_NAME, self.states, self.identifier)
        _attrib = ATTRIB_MAP.get("device_automation")

        _data = setup_sensor(HOSTNAME, "trigger_turn_on", "device_automation", _attrib)
        _data[PAYLOAD].update(self.device)
        _data[PAYLOAD].update(DEVICE_AVAILABILITY)

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
            topic = f"{MQTT_DEVICE_PREFIX}/{HOSTNAME}/{_service}"
            self._connector.subscribe_to(topic)

    ###########################################################
    def _setup_module_sensors(self, _module):
        """Configure sensors from loaded module"""

        _sensors = self._modules[_module].sensors
        if not _sensors:
            return

        _sensor_types = self._modules[_module].sensor_types
        if _sensor_types:
            self._sensor_types.update(_sensor_types)

        _sensor_attribs = self._modules[_module].sensor_attribs
        if _sensor_attribs:
            self._sensor_attribs.update(_sensor_attribs)

        _sensors_set = self._modules[_module].sensors_set
        for _sensor in _sensors:
            LOGGER.info(
                "%s Setup sensor %s for module %s", LOG_PREFIX, _sensor, _module
            )
            self.sensors[_sensor] = {}
            if _sensor in _sensors_set and hasattr(self._modules[_module], "set"):
                LOGGER.info("%s Setup callback %s.set()", LOG_PREFIX, _sensor)
                self._callback[_sensor] = self._modules[_module].set

    ###########################################################
    def _setup_sensors(self):
        """Publish sensor config to MQTT broker"""

        for sensor in tuple(self.sensors.keys()):
            _name = sensor.title().replace("_", " ")
            _type = self._sensor_types.get(sensor, "sensor")
            LOGGER.debug("%s setup_sensor %s type %s ", LOG_PREFIX, sensor, _type)

            _attribs = self._sensor_attribs.get(_type)
            _data = setup_sensor(HOSTNAME, _name, _type, _attribs)

            _data[PAYLOAD].update(DEVICE_AVAILABILITY)
            device = {"device": {"identifiers": self.identifier}}
            _data[PAYLOAD].update(device)

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

            elif isinstance(_state, int) and int(_state) not in range(0, 100000):
                continue

            elif isinstance(_state, bytearray):
                _data = {TOPIC: _topic, PAYLOAD: _state}
                self.message_send(_data)
                continue

            LOGGER.debug(
                "%s sensor[%s] state: %s %s", LOG_PREFIX, sensor, _state, type(_state)
            )

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

        LOGGER.debug("%s Done updating sensors", LOG_PREFIX)

    ###########################################################
    def _setup_device_tracker(self):
        """Publish device_tracker to MQTT broker"""

        _attribs = self._sensor_attribs.get("device_tracker")
        _data = setup_sensor(HOSTNAME, "location", "device_tracker", _attribs)
        LOGGER.debug("%s Setup device_tracker %s", LOG_PREFIX, f"{HOSTNAME}_location")

        _data[PAYLOAD].update(DEVICE_AVAILABILITY)
        _data[PAYLOAD].update(
            {
                "device": {"identifiers": self.identifier},
                "name": f"{HOSTNAME}_location",
                "source_type": "router",
            }
        )
        self.message_send(_data)

        _data[PAYLOAD].update({"name": FRIENDLY_NAME})
        self.message_send(_data)

    ###########################################################
    def update_device_tracker(self):
        """Publish device_tracker to MQTT broker"""

        unique_id = f"{self.states['hostname']}_location"
        LOGGER.debug("%s Running device_tracker.%s update", LOG_PREFIX, unique_id)

        location = "not_home"
        for _net, _loc in IP_LOCATION_MAP.items():
            if self.states["ip_address"].startswith(_net):
                location = _loc

        _topic = f"{MQTT_HA_PREFIX}/device_tracker/{unique_id}/state"
        self.message_send({TOPIC: _topic, PAYLOAD: f"{location}"})

        payload = {
            "source_type": "router",
            "hostname": HOSTNAME,
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
            _topic = f"{MQTT_HA_PREFIX}/device_tracker/{unique_id}/attrib"
            self.message_send({TOPIC: _topic, PAYLOAD: payload})
