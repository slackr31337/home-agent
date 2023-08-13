"""Home Agent connector using Home Assistant API over HTTPS"""

import asyncio
import aiohttp
import ssl
import time


from service.version import __version__
from service.log import LOGGER
from service.const import ID, TYPE

WEBSOCKET_TIMEOUT = 10  # seconds
LOG_PREFIX = r"[homeassistant_api]"


#########################################
class Connector:
    name = "homeassistant_api"
    websocket_url = None
    _websocket = None
    _ha_url = None
    _sslcontext = None
    _message_id = 1
    _last_ping = 0

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

        self._conn = aiohttp.TCPConnector()
        self._event_loop = asyncio.get_event_loop()

        self._connected = False
        self._callback = None
        self._ha_version = None
        self._setup_urls()

    ##########################################
    def _setup_urls(self) -> None:
        """Setup Home-Assistant and Websocket URLs"""

        server = self._config.api.host
        port = self._config.api.port
        proto = "http"

        self.websocket_url = "ws"
        if self._config.api.ssl:
            self._sslcontext = ssl.create_default_context(
                purpose=ssl.Purpose.CLIENT_AUTH
            )
            proto += "s"
            self.websocket_url = proto

        self._ha_url = f"{proto}://{server}:{port}"
        self.websocket_url += f"://{server}:{port}/api/websocket"

    #########################################
    def start(self):
        """Start the connector"""

        LOGGER.info("%s API connecting to %s", LOG_PREFIX, self._config.api.host)
        self._event_loop.run_until_complete(self._connect())

    ##########################################
    async def _connect(self) -> None:
        """Connect to Websocket"""

        async with aiohttp.ClientSession(connector=self._conn) as session:
            async with session.ws_connect(
                self.websocket_url,
                ssl=self._sslcontext,
                timeout=WEBSOCKET_TIMEOUT,
            ) as self._websocket:
                await self._auth_ha()
                await self._ping()

    ##########################################
    async def _auth_ha(self) -> None:
        """Authenticate websocket connection to HA"""

        LOGGER.info("Authenticating to: %s", self.websocket_url)

        self._connected = False
        msg = await self._websocket.receive_json()
        assert msg[TYPE] == "auth_required", msg

        await self._websocket.send_json(
            {
                TYPE: "auth",
                "access_token": self._config.api.token,
            }
        )

        msg = await self._websocket.receive_json()
        if msg.get(TYPE) == "auth_ok":
            LOGGER.info(
                "Authenticated to Home Assistant version %s", msg.get("ha_version")
            )
            self._connected = True
        else:
            LOGGER.error("Failed to authenticate with Home Assistant")

    ##########################################
    async def _ping(self):
        """Send Ping to HA"""

        if not self._connected:
            return

        # now = int(time.time())
        # if now - self._last_ping < 30:
        #    await asyncio.sleep(0.3)
        #    return

        await self._send_ws({TYPE: "ping"})
        response = await self._websocket.receive_json(timeout=WEBSOCKET_TIMEOUT)
        if response.get(TYPE) == "pong":
            self._connected = True

        else:
            self._connected = False

        self._last_ping = int(time.time())

    ##########################################
    async def _send_ws(self, message: dict) -> None:
        """Send Websocket JSON message and increment message ID"""

        if not self._connected:
            LOGGER.error("WS not connected")
            return

        if not isinstance(message, dict):
            LOGGER.error("Invalid WS message type")
            return

        message[ID] = self._message_id
        LOGGER.debug("send_ws() message=%s", message)

        await self._websocket.send_json(message)
        self._message_id += 1

        return await self._websocket.receive_json(timeout=WEBSOCKET_TIMEOUT)

    #########################################
    def stop(self):
        """Stop the connector"""

        self._connected_event.clear()
        self._websocket = None

    #########################################
    def connected(self):
        """Return bool for connected status"""

        self._event_loop.run_until_complete(self._ping())

        if self._connected:
            self._connected_event.set()
        else:
            self._connected_event.clear()

        return self._connected

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

        #self._client.trigger_service(
        #    domain=domain, service=service, service_data=service_data
        #)

    #########################################
    def set_state(self, entity_id, state, attrib=None):
        """Set state and attributes for entity"""

        #entity = self._client.get_entity(entity_id=entity_id)

        #entity.state.state = state
        #if attrib is not None:
        #    for key, value in tuple(attrib.items()):
        #        entity.state.attributes[key] = value

        #entity.set_state(entity.state)
