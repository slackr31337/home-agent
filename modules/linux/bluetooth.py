"""Class to scan for bluetooth devices"""

import bluetooth


from log import LOGGER

SLUG = "bluetooth"
LOG_PREFIX = f"[{SLUG}]"
#########################################
class agent_module:

    name = "Bluetooth module"
    slug = SLUG
    platform = ["linux"]
    services = {}
    state = {}
    sensors = ["bluetooth"]
    sensors_set = ["disable_scan"]
    sensor_types = {
        "bluetooth": "sensor",
        "disable_scan": "switch",
    }
    sensor_attribs = {
        "switch": {
            "topic": "~/state",
            "value_template": "{{ value_json.state }}",
            "json_attributes_topic": "~/attrib",
            "command_topic": "~/set",
        },
    }

    ###############################################################
    def __init__(self):
        self._available = True
        self._disable_scan = False
        self._set = {
            "disable_scan": self._disable_scan,
        }

    ###############################################################
    def available(self):
        return self._available

    ###############################################################
    def get(self, _method):
        """Return state for given method"""
        LOGGER.debug("%s get: %s", LOG_PREFIX, _method)
        if hasattr(self, _method):
            _func = getattr(self, _method)
            LOGGER.debug("%s function: %s", LOG_PREFIX, _func.__name__)
            return _func()

        _obj = self._set.get(_method)
        if _obj is not None:
            _value = "ON" if _obj else "OFF"
            LOGGER.debug("%s sensor %s %s", LOG_PREFIX, _method, _value)
            return _value

        LOGGER.error("%s Failed to get %s", LOG_PREFIX, _method)

    ###############################################################
    def set(self, _item, _value):
        """Set value for given item. HA switches, etc"""
        LOGGER.debug("%s set: %s value: %s", LOG_PREFIX, _item, _value)
        if _item in self._set:
            self._set[_item] = bool(_value == "ON")
        return _value

    ##############################################################
    def disable_scan(self, _value=None):
        """Home Assistant switch"""
        if _value is not None:
            self._disable_scan = bool(_value == "ON")

        return self._disable_scan

    ##############################################################
    def bluetooth(self):
        """Scan for bluetooth devices"""
        result = None
        # devices = bluetooth.discover_devices(lookup_names=True, lookup_class=True)
        # LOGGER.debug(devices)
        return result
