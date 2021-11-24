"""Home Agent connector using Home Assistant API over HTTPS"""

import homeassistant_api


from log import LOGGER

#########################################
class connector(homeassistant_api.Client):

    name = "homeassistant_api"

    #########################################
    def __init__(
        self,
        _args,
        _connected,
        **kwargs,
    ):
        self._connected_event = _connected
        self._connected = False
        super(connector, self).__init__(_args.api_url, _args.api_token, **kwargs)

    #########################################
    def connected(self):
        """Return bool for connected status"""
        self._connected = self.check_api_running()
        if self._connected:
            self._connected_event.set()
        else:
            self._connected_event.clear()
        return self._connected

    #########################################
    def start(self):
        """Start the connector"""
        self.connected()
        info = self.get_discovery_info()
        LOGGER.debug(info)

    #########################################
    def service(self, domain, service, **service_data):
        """Call a homeassistant service"""

        print(self.get_domains())
        self.trigger_service(domain=domain, service=service, service_data=service_data)

    #########################################
    def set_state(self, entity_id, state, attrib=None):
        """Set state and attribuest for entity"""
        entity = self.get_entity(entity_id=entity_id)

        entity.state.state = state
        if attrib is not None:
            for key, value in tuple(attrib.items()):
                entity.state.attributes[key] = value

        entity.set_state(entity.state)
