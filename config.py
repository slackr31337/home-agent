"""Configuration constants"""

import os
import platform


FRIENDLY_NAME = "Rob's Laptop"
HOSTNAME = str(platform.uname().node).lower()
PLATFORM = str(platform.system()).lower()

EVENT_LOOP_DELTA = 300
METRICS_DELTA = 30

API_URL = os.environ.get("API_URL", "http://homeassistant.local")
API_TOKEN = os.environ.get("API_TOKEN", "Long-Lived Access Token")

MQTT_USER = os.environ.get("MQTT_USER", "")
MQTT_PASS = os.environ.get("MQTT_PASS", "")
MQTT_HOST = os.environ.get("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))

DEFAULT_CONNECTOR = os.environ.get("DEFAULT_CONNECTOR", "mqtt")

HOME_PREFIX = "10.30.0."
WORK_PREFIX = "192.168.16."

IP_LOCATION_MAP = {
    HOME_PREFIX: "home",
    WORK_PREFIX: "I-Evolve",
}

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


MQTT_HA_PREFIX = "homeassistant"
MQTT_DEVICE_PREFIX = "devices"
MQTT_TOPICS = ["command", "event"]

MQTT_SUBS = ["homeassistant/status"]
for topic in MQTT_TOPICS:
    MQTT_SUBS.append(f"{MQTT_DEVICE_PREFIX}/{HOSTNAME}/{topic}")

DEVICE_AVAILABILITY = {
    "availability": {
        "topic": f"{MQTT_DEVICE_PREFIX}/{HOSTNAME}/availability",
    }
}

TYPE_MAP = {
    "device_automation": "device_automation",
    "battery_plugged_in": "binary_sensor",
}

SENSOR_MAP = {
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
        "topic": f"{MQTT_DEVICE_PREFIX}/{HOSTNAME}/trigger_action",
    },
    "switch": {
        "topic": "~/state",
        "value_template": "{{ value_json.state }}",
        "json_attributes_topic": "~/attrib",
        "command_topic": "~/set",
    },
}


if PLATFORM == "linux":
    TMP_DIR = "/tmp"

elif PLATFORM == "windows":
    TMP_DIR = "c:\windows\temp"
