"""Configuration constants"""

import platform
import tempfile
import yaml


CONFIG_FILE = "config.yaml"
TMP_DIR = tempfile.tempdir
HOSTNAME = str(platform.uname().node).lower()
PLATFORM = str(platform.system()).lower()

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
}

HA_PREFIX = "homeassistant"
DEVICE_PREFIX = "devices"
TOPICS = ["command", "event"]

SUBS = ["homeassistant/event"]
for topic in TOPICS:
    SUBS.append(f"{DEVICE_PREFIX}/{HOSTNAME}/{topic}")

DEVICE_AVAILABILITY = {
    "availability": {
        "topic": f"{DEVICE_PREFIX}/{HOSTNAME}/availability",
    }
}

TYPE_MAP = {
    "device_automation": "device_automation",
    "battery_plugged_in": "binary_sensor",
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
    "battery_plugged_in": {"device_class": "plug"},
    "processor_percent": {"state_class": "measurement", "unit_of_measurement": "%"},
    "memory_percent": {"state_class": "measurement", "unit_of_measurement": "%"},
}

SENSOR_PREFIX_MAP = {
    "k10temp_": {"state_class": "measurement", "unit_of_measurement": "C"},
    "w83795g_temp": {"state_class": "measurement", "unit_of_measurement": "C"},
    "w83795g_fan": {"state_class": "measurement", "unit_of_measurement": "RPM"},
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
        "json_attributes_topic": "~/state",
        "json_attributes_topic": "~/attrib",
    },
    "device_automation": {
        "automation_type": "trigger",
        "type": "action",
        "subtype": "turn_on",
        "topic": f"{DEVICE_PREFIX}/{HOSTNAME}/trigger_action",
    },
    "switch": {
        "topic": "~/state",
        "value_template": "{{ value_json.state }}",
        "json_attributes_topic": "~/attrib",
        "command_topic": "~/set",
    },
}

#########################################
def load_config(_file=CONFIG_FILE):
    """Load configuration from yaml"""
    with open(_file, "r", encoding="utf-8") as conf:
        _config = yaml.safe_load(conf)

    params = {
        "subscriptions": SUBS,
        "prefix": {"ha": HA_PREFIX, "device": DEVICE_PREFIX},
        "sensors": {
            "prefix": SENSOR_PREFIX_MAP,
            "sensor_class": CLASS_MAP,
            "type": TYPE_MAP,
            "attrib": ATTRIB_MAP,
            "publish": PUBLISH_SENSORS,
            "availability": DEVICE_AVAILABILITY,
        },
    }
    params.update(_config)
    params["hostname"] = HOSTNAME
    params["platform"] = PLATFORM
    params["temp_dir"] = TMP_DIR
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
    def items(self):
        return self.__dict.items()

    #########################################
    def update(self, items):
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
        self.__dict[name] = value

    #########################################
    def __delitem__(self, name):
        del self.__dict[name]

    #########################################
    def __getattr__(self, name):
        """Object-like access / updates"""
        return self[name]

    #########################################
    def __setattr__(self, name, value):
        self[name] = value

    #########################################
    def __delattr__(self, name):
        del self[name]

    #########################################
    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self.__dict)

    #########################################
    def __str__(self):
        return str(self.__dict)