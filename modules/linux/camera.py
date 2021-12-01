"""Class to send notifications to Linux desktop"""

import plyer

from config import TMP_DIR

################################################################
class AgentModule:

    name = "Camera module"
    slug = "camera"
    platform = ["linux"]
    sensors = []
    attribs = {}
    sensors_set = []
    sensor_types = {}
    sensor_attribs = {}
    sensor_class = {}
    services = {}

    ###############################################################
    def __init__(self):
        self._available = True
        self._camera = None

    ###############################################################
    def available(self):
        return self._available

    ###############################################################
    def picture(self):
        """Take a picture"""
        filename = f"{TMP_DIR}/picture"
        plyer.take_picture(filename)