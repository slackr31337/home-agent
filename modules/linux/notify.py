"""Class to send notifications to Linux desktop"""

import plyer

################################################################
class AgentModule:

    name = "Notify module"
    slug = "notify"
    platform = ["linux"]
    sensors = []
    attribs = {}
    sensor_class = {}
    services = {"notify": ["title", "message"]}

    ###############################################################
    def __init__(self):
        self._available = True

    ###############################################################
    def available(self):
        return self._available

    ###############################################################
    def notify(self, data):
        title = data.get("title", "HomeAgent Notification")
        message = data.get("message", "")
        timeout = int(data.get("timeout", 600))
        plyer.notification.notify(
            app_name="Home Agent",
            title=title,
            message=message,
            timeout=timeout,
            ticker="Home Agent Notification",
        )
