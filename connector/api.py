"""Home Agent connector using Home Assistant API over HTTPS"""

import json
import asyncio
from hass_client import HomeAssistantClient


from service.version import __version__
from service.log import LOGGER
from service.const import TOPIC, PAYLOAD


LOG_PREFIX = r"[homeassistant_api]"
#########################################
class Connector:

    name = "homeassistant_api"

    #########################################
    def __init__(
        self,
        config,
        connected,
        client_id,
    ):
        self._connected_event = connected
        self._config = config
        self._client_id = client_id

        self._request_id = 0
        self._connected = False
        self._callback = None
        self._ha_version = None
        self._client = HaClient(
            f"wss://{self._config.api.host}/api/websocket", self._config.api.token
        )

        # self.pool = ThreadPoolExecutor()

    #########################################
    def start(self):
        """Start the connector"""
        LOGGER.info("%s API connecting to %s", LOG_PREFIX, self._config.api.host)

        result = self._client.connect()
        LOGGER.debug(result)

        # self._ha_version = result.get("ha_version")
        LOGGER.info(
            "%s API connecting to Homeassistant %s", LOG_PREFIX, self._ha_version
        )

        result = self.ws_request(
            "auth", {"api_password": self._config.api.token}, False
        )

        _type = result.get("type")
        if result is None or _type is None:
            LOGGER.error(result)
            return False

        if _type == "auth_invalid":
            LOGGER.error("%s API auth failed. %s", LOG_PREFIX, result.get("message"))
            return False

        return self.connected()

    #########################################
    def ws_request(self, _type, _data, _id=True):
        """Send WS request and return response"""

        _request = {}
        if _type:
            _request = {"type": _type}

        if _type and _id:
            _request["id"] = self._request_id

        if _data:
            _request.update(_data)

        LOGGER.debug("ws request: %s", _request)
        if len(_request) > 0:
            message = json.dumps(_request)
        else:
            message = ""

        response = ""

        LOGGER.debug("ws result: %s", response)
        if not isinstance(response, str) or len(response) == 0:
            LOGGER.error("%s Failed to get a WS response", LOG_PREFIX)
            return None

        result = json.loads(response)
        self._request_id += 1
        return result

    #########################################
    def stop(self):
        """Stop the connector"""
        self._thread.stop()

    #########################################
    def connected(self):
        """Return bool for connected status"""
        self._connected = self.ping()
        if self._connected:
            self._connected_event.set()
        else:
            self._connected_event.clear()
        return self._connected

    #########################################
    def ping(self, topic=None):
        """Send ping message"""

        response = self.ws_request("ping")
        if response and "pong" in response:
            return True
        return False

    #########################################
    def subscribe_to(self, topic):
        """Subscribe to topic"""
        LOGGER.debug("%s subscribe: %s", LOG_PREFIX, topic)

    #########################################
    def publish(self, topic, payload):
        """Send ping message"""
        LOGGER.debug("%s publish: %s", LOG_PREFIX, topic)
        # _data = {TOPIC: topic, PAYLOAD: payload}

    #########################################
    def message_callback(self, callback):
        """Save function for forwarding messages"""
        self._callback = callback

    #########################################
    def message_receive(self, ws, message):
        """Receive a message"""
        LOGGER.debug(message)
        if self._callback is not None:
            self._callback(message)

    #########################################
    def service(self, domain, service, **service_data):
        """Call a homeassistant service"""

        self._client.trigger_service(
            domain=domain, service=service, service_data=service_data
        )

    #########################################
    def set_state(self, entity_id, state, attrib=None):
        """Set state and attribuest for entity"""
        entity = self._client.get_entity(entity_id=entity_id)

        entity.state.state = state
        if attrib is not None:
            for key, value in tuple(attrib.items()):
                entity.state.attributes[key] = value

        entity.set_state(entity.state)


#########################################
class HaClient(HomeAssistantClient):
    def __init__(self, url, token):
        self._url = url
        self._token = token
        self.loop = asyncio.get_event_loop()
        asyncio.set_event_loop(self.loop)
        asyncio.events._set_running_loop(self.loop)
        # super(HaClient, self).__new__(HomeAssistantClient)
        self._async_init()

    def __await__(self):
        return self._async_init().__await__()

    async def _async_init(self):
        # self._client = await HomeAssistantClient(self._url, self._token)
        # await self._client.__init__(self._url, self._token)
        # self.websocket = await self._client.__aenter__()
        return self

    async def connect(self):
        async with HomeAssistantClient(self._url, self._token) as client:
            client.register_event_callback(log_events)
            client.connect()
            await asyncio.sleep(360)
        await self.websocket.connect()
        self._connected = await self.websocket.connected()
        LOGGER.debug("connected=%s", self._connected)
        return self.connected()


#########################################
def log_events(event: str, event_data: dict) -> None:
    """Log node value changes."""

    LOGGER.info("Received event: %s", event)
    LOGGER.debug(event_data)
