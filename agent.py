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
from utilities.states import ThreadSafeDict, load_states, save_states
from utilities.util import calc_elasped, gps_moving, gps_update
from device.setup import setup_device, setup_sensor
from scheduler import Scheduler
from config import ONLINE_ATTRIB, Config
from const import (
    ATTRIBS,
    STATE,
    TOPIC,
    PAYLOAD,
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
    STATE_TOPIC,
    AVAILABILITY_TOPIC,
    ROUTER,
    HOSTNAME,
    BATTERY_PERCENT,
    BATTERY_LEVEL,
    BINARY_SENSOR,
    SOURCE_TYPE,
    STATUS,
    GET,
    CONNECTED,
    RESET,
    GPS,
)

LOG_PREFIX = r"[HomeAgent]"
##########################################
class HomeAgent:  # pylint:disable=too-many-instance-attributes
    """Class to collect and report endpoint data"""

    ##########################################
    def __init__(
        self,
        config: Config,
        running: threading.Event,
        sched: Scheduler,
        sensors: dict = None,
    ):
        """Init class"""
        self._connected_event = threading.Event()
        self._config = config
        self._running = running
        self._sched = sched
        self._sensors = ThreadSafeDict()
        self._states = ThreadSafeDict()
        self._attribs = ThreadSafeDict()
        self._stats = {LAST: {}}
        self._connector = None
        self._ha_connected = False
        self._modules = {}
        self._callback = {}
        self._services = {}
        self._last_sensors = {}
        self.platform_class = None
        self.device = {}
        self.icons = {}

        if sensors is None:
            sensors = self._config.sensors.get(PUBLISH)

        with self._sensors as _sensors:
            _sensors.update(sensors)

        self._os_module()
        self._connector_module()
        self._load_hardware()
        self._load_modules()
        self.get_sensors()

    ##########################################
    def stop(self):
        """Send offline message and stop connector"""

        LOGGER.info("%s Stopping", LOG_PREFIX)
        self._publish_online(OFFLINE)
        for module, mod_class in self._modules.items():
            LOGGER.info("%s Stopping %s", LOG_PREFIX, module)
            if hasattr(mod_class, "stop"):
                mod_class.stop()

        LOGGER.info("%s Disconnect from HA", LOG_PREFIX)
        self._connected_event.clear()
        self._connector.stop()
        self._connector = None
        self._ha_connected = False
        LOGGER.info("%s Exit", LOG_PREFIX)
        sys.exit()

    ##########################################
    def start(self):
        """Init system info and sensors"""

        LOGGER.debug("%s Running startup tasks", LOG_PREFIX)
        start = int(time.time())
        self._stats[START_TIME] = start
        self._load_state()
        self.get_sensors()
        self.get_identifiers()
        self.get_connections()
        self._publish_device()

        LOGGER.info(
            "%s Starting connection ping task. interval: %s",
            LOG_PREFIX,
            self._config.intervals.ping,
        )
        self._sched.queue(self.conn_ping, self._config.intervals.ping, True)

        self._add_sensor_prefixes()
        self._setup_module_sensors()
        self._setup_module_services()
        self._setup_sensors()
        self._setup_device_tracker()

        LOGGER.info(
            "%s Starting collector task. interval: %s",
            LOG_PREFIX,
            self._config.intervals.collector,
        )
        self._sched.queue(self.collector, self._config.intervals.collector, True)

        LOGGER.info(
            "%s Starting publisher task. interval: %s",
            LOG_PREFIX,
            self._config.intervals.publish,
        )
        self._sched.queue(self.publish_sensors, self._config.intervals.publish, True)

        if GPS in self._modules:
            LOGGER.info(
                "%s Starting GPS task. interval: %s",
                LOG_PREFIX,
                self._config.intervals.gps,
            )
            with self._states as _states:
                _states["has_gps"] = True
            self._sched.queue(self.gps, self._config.intervals.gps, True)
        else:
            self.update_device_tracker()

        LOGGER.info(
            "%s Starting events task. interval: %s",
            LOG_PREFIX,
            self._config.intervals.events,
        )
        self._sched.queue(self.events, self._config.intervals.events, True)

        self.collector()

        elasped = calc_elasped(start)
        LOGGER.info("%s Startup finished in %s", LOG_PREFIX, elasped)

    ##########################################
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

    ##########################################
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

        self._connector.callback(self.message_receive)
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

    ##########################################
    def _load_hardware(self):
        """Load hardware modules"""
        hw_dir = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "hardware",
        )
        sys.path.append(hw_dir)

        LOGGER.debug("%s Loading HW modules from %s", LOG_PREFIX, hw_dir)
        hw_mods = glob.glob(os.path.join(hw_dir, "*.py"))

        for _mod in hw_mods:
            _name = pathlib.Path(_mod).stem
            LOGGER.info("%s Import HW module: %s", LOG_PREFIX, _name)

            _module = importlib.import_module(_name)
            _mod_class = getattr(_module, "HWModule")
            if _mod_class.hardware != self.platform_class.hardware:
                LOGGER.info(
                    "%s HW module %s not supported on %s",
                    LOG_PREFIX,
                    _mod_class.name,
                    self.platform_class.hardware,
                )
                continue
            try:
                _class = _mod_class(self._config)
                if not _class.available():
                    LOGGER.warning("%s [%s] Not available", LOG_PREFIX, _class.name)
                    continue

                self._modules[_class.slug] = _class
                # self._setup_module_sensors(_class.slug)

            except Exception as err:  # pylint: disable=broad-except
                LOGGER.error(
                    "%s Failed to load HW module %s. %s", LOG_PREFIX, _name, err
                )
                LOGGER.debug(traceback.format_exc())

    ##########################################
    def _load_modules(self):
        """Load sensor modules"""

        mod_dir = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            f"modules/{self._config.platform}",
        )
        sys.path.append(mod_dir)

        LOGGER.debug("%s Loading sensor modules from %s", LOG_PREFIX, mod_dir)
        _mods = glob.glob(os.path.join(mod_dir, "*.py"))

        for _mod in _mods:
            _name = pathlib.Path(_mod).stem
            LOGGER.info(
                "%s Import module: %s-%s", LOG_PREFIX, self._config.platform, _name
            )

            try:
                _module = importlib.import_module(_name)

            except Exception as err:  # pylint: disable=broad-except
                LOGGER.error("%s Failed to load module %s. %s", LOG_PREFIX, _name, err)
                LOGGER.debug(traceback.format_exc())
                continue

            if not hasattr(_module, "AgentModule"):
                LOGGER.error(
                    "%s Failed to load module %s. AgentModule class not found",
                    LOG_PREFIX,
                    _module,
                )
                continue

            _mod_class = getattr(_module, "AgentModule")

            try:
                _class = _mod_class(self._config)

            except Exception as err:  # pylint: disable=broad-except
                LOGGER.error("%s Failed to load module %s. %s", LOG_PREFIX, _name, err)
                LOGGER.debug(traceback.format_exc())
                continue

            if not _class.available():
                LOGGER.warning("%s [%s] Not available", LOG_PREFIX, _class.slug)
                continue

            LOGGER.info("%s [%s] Loaded %s", LOG_PREFIX, _class.slug, _class.name)
            self._modules[_class.slug] = _class

    ##########################################
    def _conn_reset(self):
        """Reset HA connection"""
        self._stats[LAST][RESET] = int(time.time())
        self._connected_event.clear()
        self._connector.stop()
        self._connector = None
        time.sleep(5)
        self._connector_module()

    ##########################################
    def conn_ping(self):
        """Ping Home Assistant connector"""
        last_reset = self._stats[LAST].get(RESET, 0)
        last_ping = self._stats[LAST].get(PING, 0)
        last_pong = self._stats[LAST].get(PONG, 0)
        delta = int(last_ping - last_pong)
        elasped = calc_elasped(last_pong)

        LOGGER.debug(
            "%s [Ping] Last response delta: %s %s ago", LOG_PREFIX, delta, elasped
        )

        if last_pong != 0 and delta > 300:
            LOGGER.warning(
                "%s Last ping response was %s ago. Restarting home-agent",
                LOG_PREFIX,
                elasped,
            )
            self._conn_reset()

        self._stats[LAST][PING] = int(time.time())
        if self._ha_connected:
            self._stats[LAST][CONNECTED] = int(time.time())
            self._connector.ping("homeassistant/status", self._config.hostname)

        else:
            reset_elasped = calc_elasped(last_reset)
            LOGGER.error(
                "%s HA is disconnected. Last connected %s ago. Last reset was %s ago.",
                LOG_PREFIX,
                elasped,
                reset_elasped,
            )
            self._conn_reset()

    ##########################################
    def _add_sensor_prefixes(self):
        """Add sensors that match prfixes"""
        prefix_sensors = self._config.sensors.get("prefix", [])
        prefix_class = tuple(self._config.sensors.prefix_class.keys())
        prefix_icon = tuple(self._config.sensors.prefix_icons.keys())

        with self._states as _states:
            sensors = tuple(_states.keys())

        for sensor in sensors:
            item = [prefix for prefix in prefix_sensors if prefix in sensor]
            if not item:
                continue

            # Add sensor to collection
            with self._sensors as _sensors:
                _sensors[sensor] = {}

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

    ##########################################
    def get_identifiers(self):
        """Get a unique identifier for this device"""

        items = [SERIAL, MAC_ADDRESS, IP_ADDRESS]
        _id = None
        with self._states as _states:
            states = _states.copy()

        while _id is None and len(items) > 0:
            _key = items.pop(0)
            _id = states.get(_key)
            if "Serial" in _id or "O.E.M." in _id:
                _id = None

        self._config.device.identifiers = _id

        LOGGER.info("%s Device identifier: %s", LOG_PREFIX, _id)

    ##########################################
    def get_connections(self):
        """Get connection identifiers for this device"""
        with self._states as _states:
            states = _states.copy()

        _conn = [[IP_ADDRESS, states.get(IP_ADDRESS)]]
        for _value in states.get("mac_addresses"):
            if _value:
                _conn.append(["mac", _value])

        self._config.device.connections = _conn
        LOGGER.info("%s Device connections: %s", LOG_PREFIX, _conn)

    ##########################################
    def get_sensors(self):
        """Collect system info"""

        self.platform_class.update()
        states, attribs = self.platform_class.state()
        with self._states as _states:
            _states.update(states)

        with self._attribs as _attribs:
            _attribs.update(attribs)

    ##########################################
    def collector(self, only: str = None):
        """Run collector to gather sensor data"""

        LOGGER.debug("%s Running sensor data collection", LOG_PREFIX)
        self._stats[LAST]["collector"] = int(time.time())
        self.get_sensors()

        LOGGER.debug("%s Running modules", LOG_PREFIX)
        for slug, mod in self._modules.items():
            if isinstance(only, str) and slug != only:
                continue

            LOGGER.debug("%s module %s sensors", LOG_PREFIX, slug)
            for _sensor in mod.sensors:
                _value, _attrib = mod.get(_sensor)
                with self._states as _states:
                    _states[_sensor] = _value

                if _attrib:
                    with self._attribs as _attribs:
                        _attribs[_sensor] = _attrib

    ##########################################
    def events(self):
        """Run tasks to publish events"""

        LOGGER.debug("%s Running events", LOG_PREFIX)
        now = int(time.time())
        self._stats[LAST]["events"] = now

        last_all = self._stats[LAST].get("update_all", 0)
        last_delta = int(now - last_all)
        update_all = bool(last_delta > 3600)
        if update_all:
            self._stats[LAST]["update_all"] = now

        self._save_state()
        if self._ha_connected:
            self._publish_online()
            with self._sensors as _sensors:
                sensors = _sensors.copy()
            self.publish_sensors(sensors, update_all)
            self.update_device_tracker()

    ##########################################
    def _save_state(self):
        """Write state dict to file"""

        with self._states as _states:
            states = _states.copy()

        with self._attribs as _attribs:
            attribs = _attribs.copy()

        _file = f"{self._config.dir}/state.json"
        save_states(_file, states, attribs, self.device)

    ##########################################
    def _load_state(self):
        """Write state dict to file"""

        _file = f"{self._config.dir}/state.json"
        if not os.path.exists(_file):
            return

        data = load_states(_file)
        if not isinstance(data, dict):
            return

        with self._states as _states:
            _states.update(data.get(STATE))

        with self._attribs as _attribs:
            _attribs.update(data.get(ATTRIBS))

    ##########################################
    def message_send(self, _data):
        """Send message to Home Assistant using connector"""
        if not self._ha_connected:
            return False

        topic = _data.get(TOPIC)
        payload = _data.get(PAYLOAD)
        if topic is None or payload is None:
            LOGGER.error("%s payload or topic missing", LOG_PREFIX)
            LOGGER.error("%s topic: %s", LOG_PREFIX, topic)
            LOGGER.error("%s payload: %s", LOG_PREFIX, payload)
            return False

        return self._connector.pub(topic, payload)

    ##########################################
    def message_receive(self, _data: dict):
        """Receive message from Home Assistant using connector"""

        LOGGER.debug("%s Message received. %s", LOG_PREFIX, _data)
        self.process_cmd(_data)

    ##########################################
    def process_cmd(self, _data: dict):
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
        if command in [EVENT, STATUS]:
            LOGGER.debug("%s Event: %s", LOG_PREFIX, command)
            self._stats[LAST][EVENT] = now

            event_type = payload.lower()
            if event_type in [BIRTH, ONLINE, PONG]:
                self._stats[LAST][event_type] = now
                if not self._ha_connected:
                    LOGGER.info("%s Home Assistant connection is online", LOG_PREFIX)
                    self._ha_connected = True
                    self._setup_sensors()
                    self._setup_device_tracker()

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
                with self._states as _states:
                    _states[sensor] = _state

                self.publish_sensors([sensor], True)

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

    ##########################################
    def _publish_online(self, state: str = "online"):
        """Publish online status"""

        if not self.message_send(
            {
                TOPIC: f"{self._config.device.topic}/status",
                PAYLOAD: state,
            }
        ):
            self._ha_connected = False

    ##########################################
    def _publish_device(self):
        """Publish device config"""

        LOGGER.debug("%s publish_device %s", LOG_PREFIX, self._config.hostname)
        with self._states as _states:
            states = _states.copy()

        self.device = setup_device(self._config, states)

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

    ##########################################
    def _setup_module_services(self):
        """Configure services from loaded module"""
        for _module, mod_class in self._modules.items():
            if not hasattr(mod_class, "services"):
                continue

            _services = mod_class.services
            for _service, items in tuple(_services.items()):
                LOGGER.info(
                    "%s [%s] Setup service %s (%s)",
                    LOG_PREFIX,
                    _module,
                    _service,
                    items,
                )
                self._services[_service] = getattr(mod_class, _service)
                topic = f"{self._config.device.topic}/{_service}"
                self._connector.subscribe_to(topic)

    ##########################################
    def _setup_module_sensors(self):
        """Configure sensors from loaded module"""

        sensor_attr = {
            "sensor_class": self._config.sensors.sensor_class,
            "sensor_types": self._config.sensors.type,
            "sensor_attribs": self._config.sensors.attrib,
            "sensor_icons": self._config.sensors.icons,
        }

        for _module, mod_class in self._modules.items():
            if not hasattr(mod_class, "sensors"):
                continue

            for attr, conf in sensor_attr.items():
                if hasattr(mod_class, attr):
                    items = getattr(mod_class, attr)
                    conf.update(items)

            if hasattr(mod_class, "sensors_set"):
                _sensors_set = mod_class.sensors_set

            else:
                _sensors_set = {}

            for sensor in mod_class.sensors:
                LOGGER.info("%s [%s] Setup sensor %s", LOG_PREFIX, _module, sensor)

                if hasattr(mod_class, "attribs"):
                    attrib = mod_class.attribs.get(sensor)
                    self._config.sensors.attrib[sensor] = attrib
                    LOGGER.debug("%s %s: %s", LOG_PREFIX, sensor, attrib)

                if sensor in _sensors_set and hasattr(mod_class, "set"):
                    LOGGER.info("%s Setup callback %s.set()", LOG_PREFIX, sensor)
                    self._callback[sensor] = mod_class.set

                _name = sensor.title().replace("_", " ")
                LOGGER.debug("%s Setup module sensor: %s", LOG_PREFIX, _name)
                data = setup_sensor(self._config, _name)
                with self._sensors as _sensors:
                    _sensors[sensor] = data

                state, attrib = mod_class.get(sensor)
                with self._states as _states:
                    _states[sensor] = state

    ##########################################
    def _setup_sensors(self):
        """Publish sensor config to MQTT broker"""
        with self._states as _states:
            states = dict(_states).copy()

        with self._sensors as _sensors:
            sensors = dict(_sensors).copy()

        for sensor in tuple(sensors.keys()):
            _state = states.get(sensor)
            if _state is None:
                continue

            _name = sensor.title().replace("_", " ")
            _data = setup_sensor(self._config, _name)
            _topic = _data.get(TOPIC).split("/config", 2)[0]

            self._connected_event.clear()
            if not self.message_send(_data):
                LOGGER.error(
                    "%s Error publishing sensor setup %s: %s", LOG_PREFIX, _name, _topic
                )
                continue

            self._connected_event.wait(4)
            _data[PAYLOAD].update(
                {NAME: _name, AVAILABILITY_TOPIC: self._config.device.availability}
            )

            if not self.message_send(_data):
                LOGGER.error("%s Error publishing sensor setup %s", LOG_PREFIX, _name)

            _data[TOPIC] = f"{_topic}/state"
            with self._sensors as _sensors:
                _sensors[sensor] = _data

            if sensor in self._callback:
                _topic = f"{_topic}/set"
                LOGGER.info("%s Sensor set subscription: %s", LOG_PREFIX, _topic)
                self._connector.subscribe_to(_topic)

        self.publish_sensors()

    ##########################################
    def publish_sensors(self, _sensors: dict = None, force_update: bool = False):
        """Send sensor data to MQTT broker"""

        if not self._ha_connected:
            LOGGER.error(
                "%s Not connected to HA and not publishing sensor data", LOG_PREFIX
            )
            return

        with self._states as _states:
            states = _states.copy()

        with self._sensors as _sensors:
            sensors = _sensors.copy()

        if _sensors is None:
            _sensors = tuple(sensors.keys())

        LOGGER.debug(
            "%s Running publish state for %s sensors and force=%s",
            LOG_PREFIX,
            len(sensors),
            force_update,
        )

        for slug in _sensors:
            _topic = sensors[slug].get(TOPIC)
            if _topic is None:
                # LOGGER.debug("%s sensor[%s] topic is None", LOG_PREFIX, slug)
                continue

            _last = self._last_sensors.get(slug)
            _state = states.get(slug)
            _data = {TOPIC: _topic, PAYLOAD: _state}

            if _state is None:
                LOGGER.debug("%s %s state is None", LOG_PREFIX, slug)
                continue

            if isinstance(_state, int) and int(_state) not in range(0, 10000):
                continue

            if isinstance(_state, bytearray):
                self.message_send(_data)
                continue

            if isinstance(_state, list) and len(_state) == 1:
                _state = next(iter(_state), [])

            elif isinstance(_state, str) and len(_state) > 0:
                _state = _state.strip()

            if force_update or (_last is not None and _state != _last):

                if not force_update:
                    LOGGER.debug(
                        "%s %s changed from [%s] to [%s]. Publishing new state",
                        LOG_PREFIX,
                        slug,
                        _last,
                        _state,
                    )

                _data = {TOPIC: _topic, PAYLOAD: {STATE: _state}}
                self.message_send(_data)
                self._last_sensors[slug] = _state
                with self._attribs as _attribs:
                    _attrib = _attribs.get(slug)

                if _attrib and _topic:
                    _topic = _topic.split("/state", 2)[0] + "/attrib"
                    self.message_send({TOPIC: _topic, PAYLOAD: _attrib})

        LOGGER.debug("%s Done updating sensors", LOG_PREFIX)

    ##########################################
    def _setup_device_tracker(self):
        """Publish device_tracker to MQTT broker"""

        unique_id = f"{self._config.hostname}_location"
        _data = setup_sensor(self._config, "location", "device_tracker")
        LOGGER.debug(
            "%s Setup device_tracker %s",
            LOG_PREFIX,
            unique_id,
        )
        source_type = ROUTER
        with self._states as _states:
            if _states.get("has_gps") is True:
                source_type = GPS

        _data[PAYLOAD].update(
            {
                NAME: unique_id,
                SOURCE_TYPE: source_type,
                AVAILABILITY_TOPIC: self._config.device.availability,
            }
        )

        if self.message_send(_data):
            _data[PAYLOAD].update({NAME: self._config.host.friendly_name})
            self.message_send(_data)

        _topic = _data.get(TOPIC).split("/config", 2)[0]
        _data[TOPIC] = f"{_topic}/state"
        with self._sensors as _sensors:
            _sensors["device_tracker"] = _data

    ##########################################
    def update_device_tracker(self):
        """Publish device_tracker to MQTT broker"""

        LOGGER.debug("%s Running device_tracker update", LOG_PREFIX)

        with self._states as _states:
            states = _states.copy()

        with self._sensors as _sensors:
            sensor = _sensors.get("device_tracker")

        _topic = sensor.get(TOPIC)
        location = "not_home"

        if states.get("has_gps") is not True:
            for _loc, _net in self._config.device_tracker.items():

                network = ipaddress.ip_network(_net)
                if network.version != 4:
                    value = states.get("ip6_address")
                else:
                    value = states.get(IP_ADDRESS)

                if value:
                    addr = ipaddress.ip_address(value)
                    if addr in network:
                        LOGGER.debug(
                            "%s ip: %s net: %s location: %s",
                            LOG_PREFIX,
                            addr,
                            network,
                            _loc,
                        )
                        location = self._config.locations.get(_loc)

        self.message_send({TOPIC: _topic, PAYLOAD: f"{location}"})

        payload = {
            SOURCE_TYPE: ROUTER,
        }
        for key in [HOSTNAME, MAC_ADDRESS, IP_ADDRESS]:
            value = states.get(key)
            if value:
                payload[key] = value

        value = int(states.get(BATTERY_PERCENT, 0))
        if value > 0:
            payload[BATTERY_LEVEL] = str(value)

        with self._attribs as _attribs:
            value = _attribs.get("location")

        if isinstance(value, dict):
            payload[SOURCE_TYPE] = GPS
            payload.update(value)

        if len(payload) > 0:
            _topic = _topic.split("/state", 2)[0] + "/attrib"
            self.message_send({TOPIC: _topic, PAYLOAD: payload})

    #######################################################
    def gps(self):
        """Check GPS data and update as needed"""

        state, data = self._modules[GPS].get("location")
        LOGGER.debug("%s GPS sensor: %s", LOG_PREFIX, state)
        if (
            not isinstance(data, dict)
            or not isinstance(state, str)
            or "3D" not in state
        ):
            LOGGER.warning("%s GPS location fix: %s", LOG_PREFIX, state)
            return

        last = self._stats[LAST].get(GPS)
        force = gps_update(last)
        moving = gps_moving(data)
        if force or moving:
            self.update_device_tracker()
            self._stats[LAST][GPS] = int(time.time())

        last_moving = self._stats[LAST].get("moving")
        if moving != last_moving:
            LOGGER.info(
                "%s GPS moving: %s speed: %s", LOG_PREFIX, moving, data.get("speed")
            )
            self._stats[LAST]["moving"] = moving
