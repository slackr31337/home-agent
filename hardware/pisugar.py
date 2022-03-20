"""
Raspberry Pi PiSugar Hat device support
https://github.com/PiSugar/PiSugar
"""

import socket


from utilities.log import LOGGER
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
    value = float(get_parse_str(resp))
    return float(f"{value:.2f}")


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
    sensors = [slug]
    for sensor in sensor_parsers:
        sensors.append(f"{slug}_{sensor}")

    attribs = {}
    sensor_class = {
        "pisugar_battery": {
            "device_class": "battery",
            "state_class": "measurement",
            "unit_of_measurement": "%",
        },
        "pisugar_battery_v": {
            "device_class": "voltage",
            "state_class": "measurement",
            "unit_of_measurement": "V",
        },
        "pisugar_battery_i": {
            "device_class": "current",
            "state_class": "measurement",
            "unit_of_measurement": "A",
        },
        "pisugar_rtc_alarm_time": {"device_class": "timestamp"},
        "pisugar_battery_power_plugged": {"device_class": "plug"},
    }
    sensor_types = {
        "pisugar_battery_charging": "binary_sensor",
        "pisugar_battery_power_plugged": "binary_sensor",
        "pisugar_battery_allow_charging": "binary_sensor",
        "pisugar_rtc_alarm_enabled": "binary_sensor",
    }
    sensor_icons = {
        "pisugar_battery_charging": "battery-charging",
        "pisugar_battery_power_plugged": "power-plug",
    }

    ##########################################
    def __init__(self, config: Config):
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
    def get(self, item: str = None):
        """Collect hardware info from serial interface"""
        LOGGER.debug("%s get() %s", LOG_PREFIX, item)
        if item == self.slug:
            return self._get_sensor("model", get_parse_str), None

        sensor = item.split(f"{self.slug}_")[1]
        parser = self.sensor_parsers.get(sensor)
        value = self._get_sensor(sensor, parser)
        return value, None

    ##########################################
    def _get_sensor(self, sensor, parser):
        """Fetch data from socket"""
        return self.get_socket_resp(bytes(f"get {sensor}", encoding="utf-8"), parser)

    ##########################################
    def _sensors(self):
        """Fetch PiSugar device sensors"""
        values = {}
        for sensor, parser in self.sensor_parsers.items():
            value = self._get_sensor(sensor, parser)
            LOGGER.debug("%s %s=%s", LOG_PREFIX, sensor, value)
            if value:
                values[sensor] = value
