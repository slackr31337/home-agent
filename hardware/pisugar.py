"""
Raspberry Pi PiSugar Hat device support
https://github.com/PiSugar/PiSugar
"""

import socket


from utilities.log import LOGGER
from utilities.states import ThreadSafeDict
from config import Config

LOG_PREFIX = "[PiSugar]"
DEFAULT_FILE = "/tmp/pisugar-server.sock"
##########################################
class HWModule:
    """Module for PiSugar battery sensors"""

    name = "PiSugar module"
    slug = "pisugar"
    platform = ["linux"]
    hardware = "raspberrypi"
    sensors = [
        "model",
        "battery",
        "battery_i",
        "battery_v",
        "battery_charging",
        "battery_power_plugged",
        "battery_allow_charging",
        "rtc_alarm_enabled",
        "rtc_alarm_time",
        "alarm_repeat",
        "safe_shutdown_level",
        "safe_shutdown_delay",
    ]
    attribs = {}

    ##########################################
    def __init__(self, config: Config):
        self._available = False
        items = config.get(self.slug)
        if items is None:
            sock_file = DEFAULT_FILE
        else:
            sock_file = items.sock_file

        self._sock_file = sock_file
        self._state = ThreadSafeDict()
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    ##########################################
    def start(self):
        """Open sock and get sensors"""
        try:
            self._sock.connect(self._sock_file)
            self._sensors()
            self._available = True

        except socket.error:
            LOGGER.error("%s Failed to open sock %s", LOG_PREFIX, self._sock_file)

    ##########################################
    def stop(self):
        """Stop socket"""
        self._sock.close()

    ##########################################
    def available(self):
        """Return bool for module available"""
        return self._available

    ##########################################
    def get(self, item):
        """Return state for given item"""
        LOGGER.debug("%s get: %s", LOG_PREFIX, item)
        with self._state as _state:
            data = _state.get(item)

        return data

    ##########################################
    def _sensors(self):
        """Fetch PiSugar device sensors"""
        values = {}
        for sensor in self.sensors:
            self._sock.send(bytes(sensor))
            data = self._sock.recv(1024)
            value = str(data).split(": ", 3)
            if len(value) == 2:
                values[sensor] = value[1]

        self._save(values)

    ##########################################
    def _save(self, values):
        """Save GPS data to dict"""
        if not isinstance(values, dict):
            return

        with self._state as _state:
            for key, value in values.items():
                if value is not None:
                    _state[key] = value
