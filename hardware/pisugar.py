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
def get_parse_str(resp: bytes) -> str:
    """Parse string from socket bytes"""
    pos = resp.find(b":")
    return str(resp[pos + 1 :], encoding="utf-8").strip(" \n")


def get_parse_float(resp: bytes) -> float:
    """Parse float from socket bytes"""
    return float(get_parse_str(resp))


def get_parse_int(resp: bytes) -> int:
    """Parse int from socket bytes"""
    return int(get_parse_str(resp))


def get_parse_bool(resp: bytes) -> bool:
    """Parse bool from socket bytes"""
    return get_parse_str(resp).lower().find("true") >= 0


##########################################
class HWModule:
    """Module for PiSugar battery sensors"""

    name = "PiSugar module"
    slug = "pisugar"
    platform = ["linux"]
    hardware = "raspberrypi"
    sensor_parsers = {
        "model": get_parse_str,
        "battery": get_parse_float,
        "battery_i": get_parse_float,
        "battery_v": get_parse_float,
        "battery_charging": get_parse_bool,
        "battery_power_plugged": get_parse_bool,
        "battery_allow_charging": get_parse_bool,
        "rtc_alarm_enabled": get_parse_bool,
        "rtc_alarm_time": get_parse_str,
        "alarm_repeat": get_parse_int,
        "safe_shutdown_level": get_parse_float,
        "safe_shutdown_delay": get_parse_int,
    }
    sensors = sensor_parsers.keys()
    attribs = {}

    ##########################################
    def __init__(self, config: Config):
        self._state = ThreadSafeDict()
        self._available = False
        items = config.get(self.slug)
        if items is None:
            sock_file = DEFAULT_FILE
        else:
            sock_file = items.sock_file

        self._sock_file = sock_file
        LOGGER.debug("%s Using socket: %s", LOG_PREFIX, self._sock_file)
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._open_socket()

    ##########################################
    def _open_socket(self):
        """Open sock and get sensors"""
        LOGGER.debug("%s Opening socket: %s", LOG_PREFIX, self._sock_file)
        try:
            self._sock.connect(self._sock_file)
            self._available = True
            self._sensors()

        except socket.error as err:
            LOGGER.error(
                "%s Failed to open sock %s %s", LOG_PREFIX, self._sock_file, err
            )

    ##########################################
    def get_socket_resp(self, cmd: bytes, parser=None):
        """Send command to socket and get response"""
        self._sock.sendall(cmd)
        for tries in range(3):
            LOGGER.debug("%s [%s] Get command %s", LOG_PREFIX, tries, cmd)
            resp = self._sock.recv(4096)
            resp = resp.replace(b"single", b"")
            resp = resp.replace(b"double", b"")
            resp = resp.replace(b"long", b"")
            if not resp:
                continue
            if parser is not None:
                return parser(resp)
            return resp

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
        for sensor, parser in self.sensor_parsers.items():
            LOGGER.debug("%s get %s", LOG_PREFIX, sensor)
            value = self.get_socket_resp(
                bytes(f"get {sensor}", encoding="utf-8"), parser
            )
            LOGGER.debug("%s %s=%s", LOG_PREFIX, sensor, value)
            if value:
                values[sensor] = value

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
