"""Class to send notifications to Linux desktop"""

import plyer

###########################################
class AgentModule:
    """Linux desktop notification support"""

    name = "Notify module"
    slug = "notify"
    platform = ["linux"]
    sensors = []
    attribs = {}
    sensor_class = {}
    services = {"notify": ["title", "message"]}

    ##########################################
    def __init__(self, config: dict):
        self._config = config
        self._available = True

    ##########################################
    def available(self):
        """Return bool for available status"""
        return self._available

    ##########################################
    def notify(self, data):
        """Display notification on desktop"""
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
