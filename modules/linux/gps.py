"""Class for gpsd client"""

import gpsd


from utilities.log import LOGGER

LOG_PREFIX = "[GPS]"
STATE_MAP = {}
################################################################
class AgentModule:

    name = "GPS module"
    slug = "gps"
    platform = ["linux"]
    sensors = ["location"]
    attribs = {}
    sensor_class = {}
    services = {}

    ###############################################################
    def __init__(self):
        self._gps = gpsd.connect()
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

        value, attribs = self._state.get(_method)
        if value in STATE_MAP:
            value = STATE_MAP.get(value)

        LOGGER.debug("%s module sensor %s %s", LOG_PREFIX, _method, value)
        return value, attribs

    ###############################################################
    def location(self):
        location = self._gps.get_current()
        position = location.position()
        LOGGER.info("%s position: %s", LOG_PREFIX, position)
        return str(position), None
