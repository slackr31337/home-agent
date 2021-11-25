"""Class for Docker container sensors on Linux"""

################################################################
class agent_module:

    name = "Docker module"
    slug = "docker"
    platform = ["linux"]
    sensors = {}
    services = {}

    ###############################################################
    def __init__(self):
        self._available = True

    ###############################################################
    def available(self):
        return self._available
