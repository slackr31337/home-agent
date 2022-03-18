"""Class to send notifications to Linux desktop"""

import plyer

################################################################
class AgentModule:
    """Windows desktop notifications module"""

    name = "Notify module"
    slug = "notify"
    platform = ["windows"]
    _available = False
    sensors = []
    attribs = {}
    sensor_class = {}
    services = {"notify": ["title", "message"]}
    sensor_icons = {}

    ###############################################################
    def __init__(self, config: dict):
        self._config = config
        self._available = True

    ###############################################################
    def available(self):
        """Return bool for available status"""
        return self._available

    ###############################################################
    def notify(self, data):
        """Create desktop notification with message"""
        title = data.get("title", "HomeAgent Notification")
        message = data.get("message", "")
        timeout = int(data.get("timeout", 1200))
        plyer.notification.notify(
            app_name="Home Agent",
            title=title,
            message=message,
            timeout=timeout,
            ticker="Home Agent Notification",
        )
