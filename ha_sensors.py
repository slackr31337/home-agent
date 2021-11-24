"""Functions for Home-Assistant sensors and devices"""

from config import MQTT_HA_PREFIX, SENSOR_MAP, SENSOR_PREFIX_MAP
from const import SENSOR, TOPIC, PAYLOAD

#######################################################
def setup_device(_name, _sysinfo, _ident):

    _data = {
        "device": {
            "name": _name,
            "identifiers": _ident,
            "connections": [["mac", _sysinfo.get("mac_address")]],
            "manufacturer": _sysinfo.get("manufacturer"),
            "model": _sysinfo.get("model"),
            "sw_version": _sysinfo.get("platform_release"),
        },
    }

    return _data


########################################################
def setup_sensor(_hostname, sensor="Status", sensor_type=SENSOR, attribs=None):

    device_name = _hostname.lower().replace(" ", "_")
    sensor_name = sensor.lower().replace(" ", "_")
    unique_id = f"{device_name}_{sensor_name}"

    topic = f"{MQTT_HA_PREFIX}/{sensor_type}/{unique_id}"
    config_topic = f"{topic}/config"

    payload = {
        "~": topic,
        "name": unique_id,
        "unique_id": unique_id,
        "state_topic": "~/state",
    }

    sensor = sensor.lower().replace(" ", "_").strip()
    for attrib in [attribs, SENSOR_MAP.get(sensor)]:
        if isinstance(attrib, dict):
            for item, value in attrib.items():
                payload[item] = value

    for _prefix, attrib in SENSOR_PREFIX_MAP.items():
        if _prefix in unique_id:
            for item, value in attrib.items():
                payload[item] = value

    return {
        TOPIC: config_topic,
        PAYLOAD: payload,
    }
