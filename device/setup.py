"""Functions to setup devices"""


from service.log import LOGGER
from service.const import (
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

LOG_PREFIX = r"[Device]"


##########################################
def setup_device(config: dict, states: dict):
    """Return dict with device data"""

    if config.device.identifiers is None:
        LOGGER.error("%s setup_device() Missing device identifier", LOG_PREFIX)
        raise Exception(  # pylint: disable=broad-exception-raised
            "Missing device identifier"
        )

    return {
        DEVICE: {
            NAME: config.host.friendly_name,
            IDENTIFIERS: config.device.identifiers,
            CONNECTIONS: config.device.connections,
            MANUFACTURER: states.get(MANUFACTURER),
            MODEL: states.get(MODEL),
            "sw_version": states.get("firmware"),
        },
    }


########################################################
def setup_sensor(
    _config: dict, sensor: str = "Status", sensor_type: str = None, attribs: dict = None
) -> dict:
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
