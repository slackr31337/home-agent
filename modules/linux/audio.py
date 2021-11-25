"""PortAudio module for Linux

dependenicy libportaudio2

"""

################################################################
class agent_module:

    name = "Portaudio module"
    slug = "portaudio"
    platform = ["linux"]
    sensors = {}
    sensors_set = []
    sensor_types = {}
    sensor_attribs = {}
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
