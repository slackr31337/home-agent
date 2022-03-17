"""Module for polling display metrics"""

import tempfile
import ctypes
import ctypes.util
from mss import mss


from utilities.log import LOGGER
from config import HOSTNAME

LOG_PREFIX = "[display]"
STATE_MAP = {True: "ON", False: "OFF"}
###########################################
class XScreenSaverInfo(ctypes.Structure):
    """Class used to get X screen status"""

    _fields_ = [
        ("window", ctypes.c_ulong),
        ("state", ctypes.c_int),
        ("kind", ctypes.c_int),
        ("til_or_since", ctypes.c_ulong),
        ("idle", ctypes.c_ulong),
        ("eventMask", ctypes.c_ulong),
    ]


###########################################
class AgentModule:
    """Display class"""

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
    sensor_class = {}
    sensor_icons = {
        "display_idle": "monitor",
        "disable_capture": "monitor-eye",
        "display_locked": "monitor-lock",
    }

    ##########################################
    def __init__(self, config: dict, timeout: int = 300):
        LOGGER.debug("%s init module", LOG_PREFIX)
        self._config = config
        self._available = False
        self._temp_file = f"{tempfile.gettempdir()}/{HOSTNAME}_screen_capture.png"
        self._state = {
            "idle_seconds": 0,
            "timeout": timeout,
            "display_idle": False,
            "display_locked": False,
            "disable_capture": False,
        }
        self._libx11 = None
        self._setup()

    ##########################################
    def _setup(self):
        """Setup libX11"""

        xscreensaver_info_pointer = ctypes.POINTER(XScreenSaverInfo)
        display_p = ctypes.c_void_p
        xid = ctypes.c_ulong
        c_int_p = ctypes.POINTER(ctypes.c_int)
        libx11path = ctypes.util.find_library("X11")

        if libx11path is None:
            raise OSError("libX11 could not be found.")

        self._libx11 = ctypes.cdll.LoadLibrary(libx11path)
        self._libx11.XOpenDisplay.restype = display_p
        self._libx11.XOpenDisplay.argtypes = (ctypes.c_char_p,)
        self._libx11.XDefaultRootWindow.restype = xid
        self._libx11.XDefaultRootWindow.argtypes = (display_p,)

        libxss_path = ctypes.util.find_library("Xss")
        if libxss_path is None:
            raise OSError("libXss could not be found.")

        self._libxss = ctypes.cdll.LoadLibrary(libxss_path)
        self._libxss.XScreenSaverQueryExtension.argtypes = display_p, c_int_p, c_int_p
        self._libxss.XScreenSaverAllocInfo.restype = xscreensaver_info_pointer
        self._libxss.XScreenSaverQueryInfo.argtypes = (
            display_p,
            xid,
            xscreensaver_info_pointer,
        )

        self._dpy_p = self._libx11.XOpenDisplay(None)
        if self._dpy_p is None:
            raise OSError("Could not open X Display.")

        _event_basep = ctypes.c_int()
        _error_basep = ctypes.c_int()
        if (
            self._libxss.XScreenSaverQueryExtension(
                self._dpy_p, ctypes.byref(_event_basep), ctypes.byref(_error_basep)
            )
            == 0
        ):
            raise OSError("XScreenSaver Extension not available on display.")

        self._xss_info_p = self._libxss.XScreenSaverAllocInfo()
        if self._xss_info_p is None:
            raise OSError("XScreenSaverAllocInfo: Out of Memory.")

        self._rootwindow = self._libx11.XDefaultRootWindow(self._dpy_p)
        self._available = True

    ##########################################
    def available(self):
        """Return bool for available status"""
        return self._available

    ##########################################
    def get(self, _method):
        """Return state for given method"""
        LOGGER.debug("%s get: %s", LOG_PREFIX, _method)
        if hasattr(self, _method):
            _func = getattr(self, _method)
            LOGGER.debug("%s module function: %s()", LOG_PREFIX, _func.__name__)
            return _func()

        _value = self._state.get(_method)
        if _value in STATE_MAP:
            _value = STATE_MAP.get(_value)
        LOGGER.debug("%s module sensor %s %s", LOG_PREFIX, _method, _value)
        return _value, None

    ##########################################
    def set(self, _item, _value):
        """Set value for given item. HA switches, etc"""
        LOGGER.debug("%s set: %s value: %s", LOG_PREFIX, _item, _value)
        if _item in self._state:
            self._state[_item] = bool(_value == "ON")
        return _value

    ##########################################
    def display_idle(self):
        """Home Assistant sensor display_idle"""
        if (
            self._libxss.XScreenSaverQueryInfo(
                self._dpy_p, self._rootwindow, self._xss_info_p
            )
            == 0
        ):
            return None, None

        self._state["idle_seconds"] = int(self._xss_info_p.contents.idle) / 1000

        if self._state["idle_seconds"] > self._state["timeout"]:
            self._state["display_idle"] = True
        else:
            self._state["display_idle"] = False

        return self._state["display_idle"], {
            "idle": self._state["idle_seconds"],
            "timeout": self._state["timeout"],
        }

    ##########################################
    def screen_capture(self):
        """Home Assistant camera with screenshot"""
        if self._state["display_idle"] or self._state["disable_capture"]:
            LOGGER.debug("%s capture_disabled", LOG_PREFIX)
            return None, None

        with mss() as sct:
            LOGGER.debug(
                "%s writing screen shot to file %s", LOG_PREFIX, self._temp_file
            )
            filename = sct.shot(
                mon=-1,
                output=self._temp_file,
            )

        imagestring = None
        with open(filename, "rb") as _image:
            imagestring = _image.read()

        return bytearray(imagestring), None
