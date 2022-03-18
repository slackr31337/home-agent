"""Class to send notifications to Linux desktop"""

import plyer

from config import TMP_DIR

###########################################
class AgentModule:
    """Class for linux camera"""

    name = "Camera module"
    slug = "camera"
    platform = ["linux"]
    _available = False
    sensors = []
    attribs = {}
    sensors_set = []
    sensor_types = {}
    sensor_attribs = {}
    sensor_class = {}
    services = {}

    ##########################################
    def __init__(self, config: dict):
        self._config = config
        self._available = True
        self._camera = None

    ##########################################
    def available(self):
        """Return bool for available status"""
        return self._available

    ##########################################
    def picture(self):
        """Take a picture"""
        filename = f"{TMP_DIR}/picture"
        plyer.take_picture(filename)  # pylint: disable=no-member
