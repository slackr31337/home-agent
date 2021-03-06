"""Functions to setup devices"""


from utilities.log import LOGGER
from const import (
    DEVICE,
    NAME,
    IDENTIFIERS,
    CONNECTIONS,
    MANUFACTURER,
    MODEL,
    SENSOR,
    UNIQUE_ID,
    STATE_TOPIC,
    TOPIC,
    PAYLOAD,
)

LOG_PREFIX = "[Device]"
##########################################
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
