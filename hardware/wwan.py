"""Class used for interfacing with 4G HAT for Raspberry Pi"""

import os
import serial
import usb


from utilities.log import LOGGER
from utilities.states import ThreadSafeDict
from config import Config

DEFAULT_SERIAL = "/dev/ttyAMA0"
AT_COMMANDS_HARDWARE = {"carrier": r"AT+COPS=?"}
WWAN_DEVICES = {
    "1bc7:1201": {
        "model": "Telit LE910C4",
        "device": "/dev/serial/by-id/usb-Android_LE910C4-NF_0123456789ABCDEF-if02-port0",
        "gps": "/dev/serial/by-id/usb-Android_LE910C4-NF_0123456789ABCDEF-if03-port0",
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
    _model = None
    _serial = None
    sensors = []

    ##########################################
    def __init__(self, config: Config):
        self._config = config
        self._state = ThreadSafeDict()
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
                _id = f"{device.idVendor}:{device.idProduct}"
                LOGGER.debug("%s Checking USB device: %s", LOG_PREFIX, _id)
                LOGGER.debug(device)
                if _id in WWAN_DEVICES:
                    usb_id = _id
                    break

        if usb_id is None:
            return

        device = WWAN_DEVICES.get(usb_id)
        LOGGER.info("%s Found USB wwan device %s ", LOG_PREFIX, device.get("model"))
        self._model = device.get("model")
        self.serial_dev = device.get("device")

        gps_dev = device.get("gps")
        self._config.gps.dev = gps_dev
        self._available = True

    ##########################################
    def _open_serial(self):
        """Open serial port"""

        if not os.path.exists(self.serial_dev):
            LOGGER.error("%s Serial device not found. %s", LOG_PREFIX, self.serial_dev)
            self._available = False
            return

        try:
            self._serial = serial.Serial(self.serial_dev, 9600, timeout=4)

        except serial.serialutil.SerialException as err:
            LOGGER.error("%s Exception %s", LOG_PREFIX, err)

    ##########################################
    def hardware_info(self):
        """Collect hardware info from serial interface"""
