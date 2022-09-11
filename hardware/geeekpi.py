"""
Raspberry Pi GeeekPi Relay Hat device support
https://wiki.52pi.com/index.php?title=EP-0099
https://github.com/geeekpi/dockerpi/tree/master/4channelRelay
"""

from smbus2 import SMBus


from service.log import LOGGER
from service.states import ThreadSafeDict
from config import Config

DEVICE_BUS = 1
DEVICE_ADDRESS = 0x10
RELAY_VALUE = {"ON": 0xFF, "OFF": 0x00}
SWITCH_VALUE = {0: "OFF", 255: "ON"}
LOG_PREFIX = "[GeeekPi]"
##########################################
class HWModule:
    """Module for GeeekPi Relays"""

    name = "GeeekPi module"
    slug = "geeekpi"
    platform = ["linux"]
    hardware = "raspberrypi"
    sensors = ["geeekpi_relay1", "geeekpi_relay2", "geeekpi_relay3", "geeekpi_relay4"]
    sensors_set = sensors
    sensor_types = {}
    sensor_icons = {}
    for sensor in sensors:
        sensor_types[sensor] = "switch"
        sensor_icons[sensor] = "electric-switch"

    ##########################################
    def __init__(self, config: Config):
        self._available = False
        self._config = config
        self._state = ThreadSafeDict()
        self._smbus = SMBus(DEVICE_BUS)
        self._load_state()
        self._available = True

    ##########################################
    def available(self):
        """Return bool for available status"""
        return self._available

    ##########################################
    def set(self, item, value):
        """Set value for given item. HA switches, etc"""
        LOGGER.debug("%s set: %s value: %s", LOG_PREFIX, item, value)

        # if _item in self._state:
        #    self._state[_item] = bool(_value == "ON")

        data = RELAY_VALUE.get(value)
        addr = str(item)[-1]
        self._smbus.write_byte_data(DEVICE_ADDRESS, int(addr), data)
        return value

    ##########################################
    def get(self, item):
        """Return state for sensor"""
        LOGGER.debug("%s get: %s", LOG_PREFIX, item)
        sensor = str(item)[-1]
        value = self._read_bus(int(sensor))
        LOGGER.debug("%s %s=%s", LOG_PREFIX, item, value)
        if value in SWITCH_VALUE:
            return SWITCH_VALUE.get(value), None
        return value, None

    ##########################################
    def _read_bus(self, addr: int):
        """Read byte from smbus address"""
        if not isinstance(addr, int):
            return None

        return self._smbus.read_byte_data(DEVICE_ADDRESS, addr)

    ##########################################
    def _load_state(self):
        """Return value from dict"""
        for addr in range(1, 5):
            value = self._read_bus(addr)
            LOGGER.debug("%s addr: %s value: %s", LOG_PREFIX, addr, value)
            with self._state as _state:
                _state[addr] = value
