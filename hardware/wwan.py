"""Class used for interfacing with 4G HAT for Raspberry Pi"""

import serial


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

##########################################
class Wwan:
    """Module for Raspberry Pi 4G wwan Hat"""

    ##########################################
    def __init__(self, config: Config):
        self._state = ThreadSafeDict()
        items = config.get("wwan")
        if items is None:
            self.serial_dev = DEFAULT_SERIAL
        else:
            self.serial_dev = config.wwan.dev

        self._serial = serial.Serial(self.serial_dev, 9600, timeout=4)

    ##########################################
    def _discover(self):
        """Discover WWAN device"""

    ##########################################
    def hardware_info(self):
        """Collect hardware info from serial interface"""
