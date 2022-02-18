"""Class for gpsd client"""

import gpsd

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
    def location(self):
        location = self._gps.get_current()
        print(location.position())
