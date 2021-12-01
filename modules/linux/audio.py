"""PortAudio module for Linux

dependenicy libportaudio2

"""

################################################################
class AgentModule:

    name = "Portaudio module"
    slug = "audio"
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
        self.available = False

    ###############################################################
    def _setup(self):
        """Setup module"""
        return

    ###############################################################
    def available(self):
        return self._available
