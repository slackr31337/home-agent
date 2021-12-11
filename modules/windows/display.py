"""Module for polling display metrics"""

import ctypes
from mss import mss


from utilities.log import LOGGER
from config import HOSTNAME, TMP_DIR

LOG_PREFIX = "[windows_display]"
################################################################
class agent_module:

    name = "Windows display module"
    slug = "windows_display"
    platform = ["windows"]
    services = {}
    sensors = ["display_idle", "screen_capture", "disable_capture", "display_locked"]
    sensors_set = ["disable_capture", "display_locked"]
    sensor_types = {
        "display_idle": "binary_sensor",
        "screen_capture": "camera",
        "disable_capture": "switch",
        "display_locked": "switch",
    }
    sensor_attribs = {
        "camera": {
            "topic": "~/state",
            "json_attributes_topic": "~/attrib",
        },
        "switch": {
            "command_topic": "~/set",
        },
    }

    ###############################################################
    def __init__(self, _timeout=300):
        LOGGER.debug("%s init module", LOG_PREFIX)
        self._user32 = ctypes.windll.User32
        self._display_idle = None
        self._disable_capture = False
        self._display_locked = False
        self._available = False
        self._timeout = _timeout
        self._idle_seconds = 0
        self._set = {
            "disable_capture": self._disable_capture,
            "display_locked": self._display_locked,
        }
        # self._setup()

    ###############################################################
    def display_idle(self):
        """Home Assistant sensor display_idle"""
        self._display_locked = bool(self.user32.GetForegroundWindow() == 0)
        self._display_idle = False

    ##############################################################
    def display_locked(self, _value=None):
        """Home Assistant switch"""
        if _value is not None:
            self._display_locked = bool(_value="ON")

        elif _value == "ON":
            ctypes.windll.user32.LockWorkStation()
            self._display_locked = True

        return self._display_locked

    ###############################################################
    def screen_capture(self):
        """Home Assistant camera with screenshot"""
        if self._display_idle or self._disable_capture:
            return None

        with mss() as sct:
            filename = sct.shot(
                mon=-1,
                output=f"{TMP_DIR}\{HOSTNAME}_screen_capture.png",
            )
        _image = open(filename, "rb")
        imagestring = _image.read()

        return bytearray(imagestring)

    ###############################################################
    def get(self, _method):
        """Return state for given method"""
        LOGGER.debug(_method)
        return None

    ###############################################################
    def set(self, _item, _value):
        """Set value for given item. HA switches, etc"""
        LOGGER.debug("%s set: %s value: %s", LOG_PREFIX, _item, _value)
        return None
