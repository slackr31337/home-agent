"""Class to scan for bluetooth devices"""

import time
from bleson import get_provider, Observer, Advertisement


from service.log import LOGGER

SLUG = r"bluetooth"
LOG_PREFIX = f"[{SLUG}]"


##########################################
class AgentModule:
    """Bluetooth scanner"""

    name = "Bluetooth module"
    slug = SLUG
    platform = ["linux"]
    services = {}
    sensors = ["bluetooth", "disable_scan"]
    attribs = {}
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

    ##########################################
    def __init__(self, config: dict):
        self._config = config
        self._available = True
        self._disable_scan = False
        self.devices = {}
        self._set = {
            "disable_scan": self._disable_scan,
        }
        _adapter = get_provider().get_adapter()
        self.scanner = Observer(_adapter)
        self.scanner.on_advertising_data = self._detection

    ##########################################
    def _detection(self, advertisement: Advertisement):
        """Store bluetooth data"""

        if advertisement.address_type == "RANDOM" or advertisement.type == "SCAN_RSP":
            return

        addr = str(str(advertisement.address).split("BDAddress('", maxsplit=1)[1])[
            :-2
        ].lower()
        distance = pow(10, ((-55 - (advertisement.rssi)) / (10 * 2)))
        _data = {
            "name": advertisement.name,
            "rssi": advertisement.rssi,
            "distance": float(f"{distance:.2f}"),
            "timestamp": int(time.time()),
            "mfg_data": advertisement.mfg_data,
            "service_data": advertisement.service_data,
        }

        self.devices[addr] = _data
        # LOGGER.info(vars(advertisement))
        # LOGGER.info(
        #    "%s [%s] %s ",
        #    LOG_PREFIX,
        #    addr,
        #    _data,
        # )

    ##########################################
    def available(self) -> bool:
        """Return bool for available"""

        return self._available

    ##########################################
    def get(self, _method: str):
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
            return _value, None

        LOGGER.error("%s Failed to get %s", LOG_PREFIX, _method)

    ##########################################
    def set(self, _item: str, _value):
        """Set value for given item. HA switches, etc"""

        LOGGER.debug("%s set: %s value: %s", LOG_PREFIX, _item, _value)
        if _item in self._set:
            self._set[_item] = bool(_value == "ON")
        return _value

    ##########################################
    def disable_scan(self, _value: str = None) -> bool:
        """Home Assistant switch"""

        if _value is not None:
            self._disable_scan = bool(_value == "ON")

        return self._disable_scan, None

    ##########################################
    def bluetooth(self):
        """Scan for bluetooth devices"""

        if self._disable_scan:
            return None, None

        self.scanner.start()
        time.sleep(5)
        self.scanner.stop()

        now = int(time.time())
        expire = now - 300
        attribs = {}
        for addr, values in tuple(self.devices.items()):
            if expire > values["timestamp"]:
                self.devices.pop(addr, None)
                continue
            attribs[addr] = values.get("distance")

        return len(self.devices), attribs
