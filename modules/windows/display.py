"""Module for polling display metrics"""

import tempfile
import ctypes
from mss import mss


from utilities.log import LOGGER
from config import HOSTNAME

LOG_PREFIX = "[display]"
################################################################
class AgentModule:

    name = "Windows display module"
    slug = "display"
    platform = ["windows"]
    services = {}
    sensors = ["display_idle", "screen_capture", "disable_capture", "display_locked"]
    sensors_set = ["disable_capture", "display_locked"]
    attribs = {}
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
    sensor_class = {}
    sensor_icons = {
        "display_idle": "monitor",
        "disable_capture": "monitor-eye",
        "display_locked": "monitor-lock",
    }
    ###############################################################
    def __init__(self, timeout=300):
        LOGGER.debug("%s init module", LOG_PREFIX)
        self._user32 = ctypes.windll.User32
        self._mss = mss()
        self._available = True
        self._temp_file = f"{tempfile.gettempdir()}/{HOSTNAME}_screen_capture.png"
        self._state = {
            "idle_seconds": 0,
            "timeout": timeout,
            "display_idle": False,
            "display_locked": False,
            "disable_capture": False,
        }

    ###############################################################
    def available(self):
        return self._available

    ###############################################################
    def get(self, _method):
        """Return state for given method"""
        LOGGER.debug("%s get: %s", LOG_PREFIX, _method)
        if hasattr(self, _method):
            _func = getattr(self, _method)
            LOGGER.debug("%s module function: %s()", LOG_PREFIX, _func.__name__)
            return _func()

        _value = self._state.get(_method)
        LOGGER.debug("%s module sensor %s %s", LOG_PREFIX, _method, _value)
        return _value, None

    ###############################################################
    def set(self, _item, _value):
        """Set value for given item. HA switches, etc"""
        LOGGER.debug("%s set: %s value: %s", LOG_PREFIX, _item, _value)
        if _item in self._state:
            self._state[_item] = bool(_value == "ON")
        return _value

    ###############################################################
    def display_idle(self):
        """Home Assistant sensor display_idle"""
        self._state["display_locked"] = bool(self.user32.GetForegroundWindow() == 0)
        self._state["idle_seconds"] = 0

        if self._state["idle_seconds"] > self._state["timeout"]:
            self._state["display_idle"] = True
        else:
            self._state["display_idle"] = False

        return self._state["display_idle"], {
            "idle": self._state["idle_seconds"],
            "timeout": self._state["timeout"],
        }

    ##############################################################
    def display_locked(self, _value=None):
        """Home Assistant switch"""
        if _value is not None:
            self._state["display_locked"] = bool(_value="ON")

        elif _value == "ON":
            ctypes.windll.user32.LockWorkStation()
            self._state["display_locked"] = True

        return self._state["display_locked"], None

    ###############################################################
    def screen_capture(self):
        """Home Assistant camera with screenshot"""
        if self._state["display_idle"] or self._state["disable_capture"]:
            LOGGER.debug("%s capture_disabled", LOG_PREFIX)
            return None, None

        with self._mss as sct:
            filename = sct.shot(
                mon=-1,
                output=self._temp_file,
            )
        with open(filename, "rb") as _image:
            imagestring = _image.read()

        return bytearray(imagestring), None

    ###############################################################
    def get(self, _method):
        """Return state for given method"""
        LOGGER.debug(_method)
        return None, None

    ###############################################################
    def set(self, _item, _value):
        """Set value for given item. HA switches, etc"""
        LOGGER.debug("%s set: %s value: %s", LOG_PREFIX, _item, _value)
        return None
