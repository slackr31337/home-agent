"""Class to scan for bluetooth devices"""

import asyncio
from bleak import BleakScanner


from log import LOGGER

SLUG = "bluetooth"
LOG_PREFIX = f"[{SLUG}]"
#########################################
class AgentModule:
    """Bluetooth scanner"""

    name = "Bluetooth module"
    slug = SLUG
    platform = ["linux"]
    services = {}
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
    attribs = {
        "bluetooth": {"unit_of_measurement": "devices"},
    }

    ###############################################################
    def __init__(self):
        self._available = True
        self._disable_scan = False
        self.devices = {}
        self._set = {
            "disable_scan": self._disable_scan,
        }
        self.scanner = BleakScanner()
        self.scanner.register_detection_callback(self.detection_callback)

    ###############################################################
    def available(self):
        return self._available

    ###############################################################
    def get(self, _method):
        """Return state for given method"""
        LOGGER.debug("%s get: %s", LOG_PREFIX, _method)
        if hasattr(self, _method):
            _func = getattr(self, _method)
            LOGGER.debug("%s return %s()", LOG_PREFIX, _func.__name__)
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
        attribs = {}
        asyncio.run(self._scan())
        for ident, values in tuple(self.devices.items()):
            attribs[ident] = values.get("distance")
        return len(self.devices), attribs

    ###############################################################
    async def _scan(self):
        """Async scan for bluetooth devices"""
        async with self.scanner as scanner:
            await asyncio.sleep(3)

    ##############################################################
    def detection_callback(self, device, advertisement_data):
        """Store bluetooth advertisement data"""
        addr = str(device.address)
        distance = pow(10, ((-55 - (device.rssi)) / (10 * 2)))
        _data = {"rssi": device.rssi, "distance": float(f"{distance:.3f}")}

        # if advertisement_data.service_uuids:
        #    _data["uuids"] = advertisement_data.service_uuids

        if advertisement_data.local_name:
            _data["name"] = advertisement_data.local_name

        self.devices[addr] = _data
        LOGGER.debug(
            "%s [%s] %s ",
            LOG_PREFIX,
            addr,
            _data,
        )
