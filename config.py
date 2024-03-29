"""Configuration constants"""

import os
import platform
import tempfile
import yaml


from service.version import __version__

CONFIG_FILE = "config.yaml"

TMP_DIR = tempfile.gettempdir()
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
OS_DIR = os.path.join(BASE_DIR, "os")
MOD_DIR = os.path.join(BASE_DIR, "modules")
CONN_DIR = os.path.join(BASE_DIR, "connector")
HW_DIR = os.path.join(BASE_DIR, "hardware")
HOSTNAME = str(platform.uname().node).lower()
PLATFORM = str(platform.system()).lower()

DISCOVER_PREFIX = "homeassistant"
DEVICE_PREFIX = "devices"
TOPICS = ["command", "event", "status"]

DEVICE_TOPIC = f"{DEVICE_PREFIX}/{HOSTNAME}"
DEVICE_STATUS = f"{DEVICE_TOPIC}/status"

SUBS = [f"{DISCOVER_PREFIX}/status"]
for topic in TOPICS:
    SUBS.append(f"{DEVICE_TOPIC}/{topic}")

PUBLISH_SENSORS = {
    "ip_address": {},
    "ip6_address": {},
    "mac_address": {},
    "last_boot": {},
    "model": {},
    "serial": {},
    "platform": {},
    "platform_release": {},
    "platform_version": {},
    "load": {},
    "processor": {},
    "processor_percent": {},
    "memory_percent": {},
    "battery_percent": {},
    "battery_plugged_in": {},
    "users": {},
}

PUBLISH_SENSOR_PREFIX = [
    "disk_",
    "network_enp",
    "network_eth",
    "network_w",
    "temp",
    "coretemp",
    "k10temp_",
    "w83795g_temp",
    "w83795g_fan",
    "acpitz",
]

ICON_MAP = {
    "ip_address": "ip-network",
    "ip6_address": "ip-network",
    "load": "format-line-weight",
    "processor_percent": "cpu-64-bit",
    "memory_percent": "chip",
    "users": "account",
}

ICON_PREFIX_MAP = {
    "memory_": "chip",
    "disk_": "harddisk",
    "network_": "network",
    "temp_": "thermometer-lines",
    "coretemp": "thermometer-lines",
    "fan": "fan",
    "acpitz_": "thermometer-lines",
}

CLASS_TEMP = {"state_class": "measurement", "unit_of_measurement": "C"}
CLASS_PERCENT = {"state_class": "measurement", "unit_of_measurement": "%"}
CLASS_RPM = {"state_class": "measurement", "unit_of_measurement": "RPM"}

PREFIX_CLASS_MAP = {
    "disk_": CLASS_PERCENT,
    "network_": {},
    "temp_": CLASS_TEMP,
    "coretemp": CLASS_TEMP,
    "k10temp": CLASS_TEMP,
    "w83795g_temp": CLASS_TEMP,
    "w83795g_fan": CLASS_RPM,
    "acpitz_": CLASS_TEMP,
}

CLASS_MAP = {
    "load": {
        "state_class": "measurement",
        "unit_of_measurement": "load",
    },
    "last_boot": {"device_class": "timestamp"},
    "battery_percent": {
        "device_class": "battery",
        "state_class": "measurement",
        "unit_of_measurement": "%",
    },
    "users": {"state_class": "measurement", "unit_of_measurement": "users"},
    "battery_plugged_in": {"device_class": "plug"},
    "processor_percent": CLASS_PERCENT,
    "memory_percent": CLASS_PERCENT,
}

ATTRIB_MAP = {
    "sensor": {
        "value_template": "{{ value_json.state }}",
        "json_attributes_topic": "~/attrib",
    },
    "binary_sensor": {
        "value_template": "{{ value_json.state }}",
        "payload_on": "True",
        "payload_off": "False",
        "json_attributes_topic": "~/attrib",
    },
    "device_tracker": {
        "source_type": "router",
        "hostname": HOSTNAME,
        "topic": "~/state",
        "json_attributes_topic": "~/attrib",
    },
    "device_automation": {
        "automation_type": "trigger",
        "type": "action",
        "subtype": "turn_on",
        "topic": f"{DEVICE_TOPIC}/rigger_action",
    },
    "switch": {
        "topic": "~/state",
        "value_template": "{{ value_json.state }}",
        "json_attributes_topic": "~/attrib",
        "command_topic": "~/set",
    },
}

ONLINE_ATTRIB = {
    "device_class": "connectivity",
    "icon": "mdi:desktop-classic",
    "expire_after": 300,
    "payload_on": "online",
    "payload_off": "offline",
    "json_attributes_topic": "~/attrib",
}

TYPE_MAP = {
    "device_automation": "device_automation",
    "battery_plugged_in": "binary_sensor",
}

APP_NAME = "Home Agent endpoint"


#########################################
def load_config(args: dict) -> dict:
    """Load configuration from yaml"""

    config_file = args.get("config", CONFIG_FILE)
    with open(config_file, "r", encoding="utf-8") as conf:
        _config = yaml.safe_load(conf)

    params = {
        "app_name": APP_NAME,
        "app_ver": f"{APP_NAME} {__version__}",
        "dir": BASE_DIR,
        "temp_dir": TMP_DIR,
        "state_file": f"{TMP_DIR}/homeagent_state.json",
        "args": args,
        "device": {
            "topic": DEVICE_TOPIC,
            "availability": DEVICE_STATUS,
            "identifiers": None,
            "connections": None,
        },
        "subscriptions": SUBS,
        "prefix": {"discover": DISCOVER_PREFIX, "device": DEVICE_PREFIX},
        "sensors": {
            "prefix": PUBLISH_SENSOR_PREFIX,
            "prefix_class": PREFIX_CLASS_MAP,
            "sensor_class": CLASS_MAP,
            "type": TYPE_MAP,
            "attrib": ATTRIB_MAP,
            "publish": PUBLISH_SENSORS,
            "icons": ICON_MAP,
            "prefix_icons": ICON_PREFIX_MAP,
        },
        "intervals": {"collector": 30, "publisher": 60},
    }
    params.update(_config)
    params["hostname"] = HOSTNAME
    params["platform"] = PLATFORM
    return params


#########################################
class Config:
    """Configuration class"""

    #########################################
    def __init__(self, _dict=None):
        object.__setattr__(self, "_Config__dict", _dict)

    #########################################
    def get(self, name, default=None):
        """Dictionary get method"""
        return self.__dict.get(name, default)

    #########################################
    def keys(self):
        """Return dictionary keys"""
        return self.__dict.keys()

    #########################################
    def items(self):
        """Return dictionary items"""
        return self.__dict.items()

    #########################################
    def update(self, items):
        """Update dictionary"""
        return self.__dict.update(items)

    #########################################
    def __getitem__(self, name):
        """Dictionary-like access / updates"""
        if name not in self.__dict:
            return None
        value = self.__dict[name]
        if isinstance(value, dict):
            value = Config(value)
        return value

    #########################################
    def __setitem__(self, name, value):
        """Dictionary set item method"""
        self.__dict[name] = value

    #########################################
    def __delitem__(self, name):
        """Dictionary del item method"""
        del self.__dict[name]

    #########################################
    def __getattr__(self, name):
        """Object-like access / updates"""
        return self[name]

    #########################################
    def __setattr__(self, name, value):
        """Dictionary set attribute method"""
        self[name] = value

    #########################################
    def __delattr__(self, name):
        """Dictionary del attribute method"""
        del self[name]

    #########################################
    def __repr__(self):
        """Dictionary method"""
        return "%s(%r)" % (  # pylint: disable=consider-using-f-string
            type(self).__name__,
            self.__dict,
        )

    #########################################
    def __str__(self):
        """Dictionary method"""
        return str(self.__dict)
