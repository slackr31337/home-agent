"""Module for polling display metrics"""

import ctypes
import ctypes.util
from mss import mss


from log import LOGGER
from config import HOSTNAME

LOG_PREFIX = "[display]"
################################################################
class XScreenSaverInfo(ctypes.Structure):
    _fields_ = [
        ("window", ctypes.c_ulong),
        ("state", ctypes.c_int),
        ("kind", ctypes.c_int),
        ("til_or_since", ctypes.c_ulong),
        ("idle", ctypes.c_ulong),
        ("eventMask", ctypes.c_ulong),
    ]


################################################################
class AgentModule:

    name = "X11 display module"
    slug = "display"
    platform = ["linux"]
    services = {}
    sensors = ["display_idle", "screen_capture", "disable_capture", "display_locked"]
    attribs = {}
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
            "topic": "~/state",
            "value_template": "{{ value_json.state }}",
            "json_attributes_topic": "~/attrib",
            "command_topic": "~/set",
        },
    }

    ###############################################################
    def __init__(self, _timeout=300):
        LOGGER.debug("%s init module", LOG_PREFIX)
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
        self._setup()

    ###############################################################
    def _setup(self):
        """Setup libX11"""

        XScreenSaverInfo_p = ctypes.POINTER(XScreenSaverInfo)
        display_p = ctypes.c_void_p
        xid = ctypes.c_ulong
        c_int_p = ctypes.POINTER(ctypes.c_int)
        libX11path = ctypes.util.find_library("X11")

        if libX11path is None:
            raise OSError("libX11 could not be found.")

        self._libX11 = ctypes.cdll.LoadLibrary(libX11path)
        self._libX11.XOpenDisplay.restype = display_p
        self._libX11.XOpenDisplay.argtypes = (ctypes.c_char_p,)
        self._libX11.XDefaultRootWindow.restype = xid
        self._libX11.XDefaultRootWindow.argtypes = (display_p,)

        libXsspath = ctypes.util.find_library("Xss")
        if libXsspath is None:
            raise OSError("libXss could not be found.")

        self._libXss = ctypes.cdll.LoadLibrary(libXsspath)
        self._libXss.XScreenSaverQueryExtension.argtypes = display_p, c_int_p, c_int_p
        self._libXss.XScreenSaverAllocInfo.restype = XScreenSaverInfo_p
        self._libXss.XScreenSaverQueryInfo.argtypes = (
            display_p,
            xid,
            XScreenSaverInfo_p,
        )

        self._dpy_p = self._libX11.XOpenDisplay(None)
        if self._dpy_p is None:
            raise OSError("Could not open X Display.")

        _event_basep = ctypes.c_int()
        _error_basep = ctypes.c_int()
        if (
            self._libXss.XScreenSaverQueryExtension(
                self._dpy_p, ctypes.byref(_event_basep), ctypes.byref(_error_basep)
            )
            == 0
        ):
            raise OSError("XScreenSaver Extension not available on display.")

        self._xss_info_p = self._libXss.XScreenSaverAllocInfo()
        if self._xss_info_p is None:
            raise OSError("XScreenSaverAllocInfo: Out of Memory.")

        self._rootwindow = self._libX11.XDefaultRootWindow(self._dpy_p)
        self._available = True

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

        _obj = self._set.get(_method)
        if _obj is not None:
            _value = "ON" if _obj else "OFF"
            LOGGER.debug("%s module sensor %s %s", LOG_PREFIX, _method, _value)
            return _value, None

        LOGGER.error("%s Failed to get %s", LOG_PREFIX, _method)

    ###############################################################
    def set(self, _item, _value):
        """Set value for given item. HA switches, etc"""
        LOGGER.debug("%s moudule set: %s value: %s", LOG_PREFIX, _item, _value)
        if _item in self._set:
            self._set[_item] = bool(_value == "ON")
        return _value

    ###############################################################
    def display_idle(self):
        """Home Assistant sensor display_idle"""
        if (
            self._libXss.XScreenSaverQueryInfo(
                self._dpy_p, self._rootwindow, self._xss_info_p
            )
            == 0
        ):
            return None, None

        self._idle_seconds = int(self._xss_info_p.contents.idle) / 1000
        attrib = {"idle": self._idle_seconds, "timeout": self._timeout}

        if self._idle_seconds > self._timeout:
            self._display_idle = True
        else:
            self._display_idle = False

        return self._display_idle, attrib

    ##############################################################
    def display_locked(self, _value=None):
        """Home Assistant switch"""
        if _value is not None:
            self._display_locked = bool(_value == "ON")

        return self._display_locked, None

    ###############################################################
    def screen_capture(self):
        """Home Assistant camera with screenshot"""
        if self._display_idle or self._disable_capture:
            return None, None

        with mss() as sct:
            filename = sct.shot(
                mon=-1,
                output=f"/tmp/{HOSTNAME}_screen_capture.png",
            )

        imagestring = None
        with open(filename, "rb") as _image:
            imagestring = _image.read()

        return bytearray(imagestring), None
