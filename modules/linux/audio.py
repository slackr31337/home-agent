"""PortAudio module for Linux

dependenicy libportaudio2

"""

###########################################
class AgentModule:
    """Class for audio device support"""

    name = "Portaudio module"
    slug = "audio"
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
        self._available = False
        self._state = {}

    ##########################################
    def _setup(self):
        """Setup module"""
        return

    ##########################################
    def available(self):
        """Return bool for available status"""
        return self._available
