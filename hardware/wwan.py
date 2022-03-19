"""Class used for interfacing with 4G HAT for Raspberry Pi"""

import os
import serial
import usb


from utilities.log import LOGGER
from utilities.states import ThreadSafeDict
from config import Config

DEFAULT_SERIAL = "/dev/ttyAMA0"
AT_COMMANDS_HARDWARE = {
    "carrier": r"AT+COPS?",
    "status": r"AT+CREG?",
    "rssi": r"AT+CSQ",
    "iemi": r"AT#IMEISV",
    "serial": r"AT+GSN",
    "manufacturer": r"AT+CGMI",
    "model": r"AT+CGMM",
    "version": r"AT+CGMR",
}
STATIC_SENSORS = ["iemi", "serial", "manufacturer", "model", "version"]
AT_MAP = {
    "status": {
        "0": "no registered",
        "1": "registered",
        "2": "searching",
        "3": "denied",
        "4": "unknown",
        "5": "roaming",
    },
    "rssi": {str(key): str(-113 + (2 * key)) for key in range(0, 31)},
}
AT_VALUE = {
    "carrier": 2,
    "status": 1,
    "rssi": 0,
}
WWAN_DEVICES = {
    "1bc7:1201": {
        "model": "Telit LE910C4",
        "device": "/dev/ttyUSB3",
        "gps": "/dev/ttyUSB1",
    }
}
LOG_PREFIX = "[Wwan]"
##########################################
class HWModule:
    """Module for Raspberry Pi 4G wwan Hat"""

    name = "4G HAT module"
    slug = "wwan"
    platform = ["linux"]
    hardware = "raspberrypi"
    _available = False
    _serial = None
    sensors = [slug]
    for sensor in AT_COMMANDS_HARDWARE:
        sensors.append(f"{slug}_{sensor}")

    sensor_icons = {
        "wwan_carrier": "sim",
        "wwan_status": "signal-variant",
        "wwan_iemi": "barcode",
        "wwan_serial": "barcode",
    }
    sensor_class = {
        "wwan_rssi": {
            "device_class": "signal_strength",
            "state_class": "measurement",
            "unit_of_measurement": "dBm",
        },
    }
    ##########################################
    def __init__(self, config: Config):
        self._config = config
        self._state = ThreadSafeDict()
        self._device = None
        items = config.get(self.slug)
        if items is None:
            self.serial_dev = DEFAULT_SERIAL
        else:
            self.serial_dev = config.wwan.dev

        self._discover()
        self._open_serial()

    ##########################################
    def stop(self):
        """Close serial device"""
        self._serial.close()

    ##########################################
    def available(self):
        """Return bool for module available"""
        return self._available

    ##########################################
    def _discover(self):
        """Discover WWAN device"""
        usb_id = None
        for bus in usb.busses():
            devices = bus.devices
            for device in devices:
                _id = f"{device.idVendor:04x}:{device.idProduct:04x}"
                LOGGER.debug("%s Checking USB device: %s", LOG_PREFIX, _id)
                if _id in WWAN_DEVICES:
                    usb_id = _id
                    break

        if usb_id is None:
            return

        self._device = WWAN_DEVICES.get(usb_id)
        LOGGER.info(
            "%s Found USB wwan device %s ", LOG_PREFIX, self._device.get("model")
        )

        self.serial_dev = self._device.get("device")
        self._config.gps = {"dev": self._device.get("gps")}
        self._available = True

    ##########################################
    def _open_serial(self):
        """Open serial port"""

        if not self.serial_dev or not os.path.exists(self.serial_dev):
            LOGGER.error("%s Serial device not found. %s", LOG_PREFIX, self.serial_dev)
            self._available = False
            return

        try:
            self._serial = serial.Serial(self.serial_dev, 9600, timeout=1)
            if not self._serial.is_open:
                LOGGER.error("%s Failed to open serial %s", LOG_PREFIX, self.serial_dev)
                return

            self._load_state()

        except serial.serialutil.SerialException as err:
            LOGGER.error("%s Exception %s", LOG_PREFIX, err)

    ##########################################
    def _at_cmd(self, command: str) -> str:
        """Send AT command to serial device"""

        LOGGER.debug("%s AT Command: %s", LOG_PREFIX, command)
        self._serial.write(f"{command}\r\n".encode(encoding="utf-8"))
        value = None
        strings = ""

        resp = self._serial.readlines()
        count = 0
        for item in resp:
            count += 1
            if count == 0:
                continue

            strings = str(item.decode(encoding="utf-8")).strip()
            if len(strings) == 0 or strings == "OK":
                continue

            if ":" in strings:
                value = strings.split(": ", maxsplit=2)[1]
            else:
                value = strings

        if not value and strings:
            value = strings

        LOGGER.debug("%s AT Value: %s", LOG_PREFIX, value)
        return value

    ##########################################
    def get(self, item: str = None):
        """Collect hardware info from serial interface"""
        LOGGER.info("%s get() %s", LOG_PREFIX, item)
        if item == self.slug:
            return self._device.get("model"), None

        sensor = item.split(f"{self.slug}_")[1]
        if sensor in self._state:
            return self._get_state(sensor), None

        command = AT_COMMANDS_HARDWARE.get(sensor)
        if not command:
            LOGGER.error("%s AT Command not found for %s", LOG_PREFIX, sensor)
            return None, None

        value = self._at_cmd(command)
        LOGGER.debug("%s result: %s", LOG_PREFIX, value)

        offset = AT_VALUE.get(sensor)
        if offset is not None:
            value = str(value).split(",", maxsplit=10)[offset]

        value_map = AT_MAP.get(sensor)
        if value_map:
            value = value_map.get(value)

        if isinstance(value, str) and '"' in value:
            value = value.replace('"', "")

        LOGGER.debug("%s %s=%s", LOG_PREFIX, sensor, value)
        return value, None

    ##########################################
    def _load_state(self):
        """Return value from dict"""
        for sensor in STATIC_SENSORS:
            command = AT_COMMANDS_HARDWARE.get(sensor)
            value = self._at_cmd(command)
            with self._state as _state:
                _state[sensor] = value

    ##########################################
    def _get_state(self, key: str = "model") -> str:
        """Return value from dict"""

        with self._state as _state:
            value = _state.get(key)
        return value
