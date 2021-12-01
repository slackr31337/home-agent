"""Class for Docker container sensors on Linux"""

################################################################
class AgentModule:

    name = "Docker module"
    slug = "docker"
    platform = ["linux"]
    sensors = []
    attribs = {}
    sensor_class = {}
    services = {}

    ###############################################################
    def __init__(self):
        self._available = True

    ###############################################################
    def available(self):
        return self._available
