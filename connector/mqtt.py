"""Class for MQTT messaging"""

import ssl
import json
import time
import platform
import socket
import threading
from paho.mqtt.client import WebsocketConnectionError, Client as Mqtt


from service.log import LOGGER
from service.const import TOPIC, PAYLOAD

if platform.system() == "Linux":
    TLS_CA_CERT = "/etc/ssl/certs/ca-certificates.crt"
    TLS_CERT = "/etc/ssl/private/mqtt_client.crt"
    TLS_KEY = "/etc/ssl/private/mqtt_client.key"

else:
    TLS_CA_CERT = None
    TLS_CERT = ""
    TLS_KEY = ""

MQTT_CONN_CODES = {
    0: "Connected",
    1: "Incorrect Protocol Version",
    2: "Invalid client identifier",
    3: "Server unavailable",
    4: "Bad username or password",
    5: "Not authorized",
    6: "Unknown",
}

LOG_PREFIX = r"[MQTT]"
##########################################
class Connector(Mqtt):
    """Home Assistant Connector class"""

    name = "mqtt"

    ##########################################
    def __init__(
        self,
        config: dict,
        event: threading.Event,
        running: threading.Event,
        clientid: str,
        **kwargs,
    ):

        if not clientid:
            clientid = f"mqtt_client_{int(time.time())}"

        super().__init__(clientid, clean_session=True, **kwargs)
        self._clientid = clientid
        self._connected_event = event
        self._running = running
        self._config = config
        self._connected = False
        self._callback = None
        self._tries = 0
        self._subscribe = []
        self._setup()

    ##########################################
    def _setup(self):
        """Setup MQTT client"""
        LOGGER.info("%s Client: %s", LOG_PREFIX, self._clientid)

        if self._config.mqtt.user:
            LOGGER.info("%s User: %s", LOG_PREFIX, self._config.mqtt.user)
            self.username_pw_set(
                username=self._config.mqtt.user, password=self._config.mqtt.password
            )

        #self.reconnect_delay_set(min_delay=3, max_delay=30)
        self.on_connect = self._on_connect
        self.on_disconnect = self._on_disconnect
        self.on_subscribe = self._on_subscribe
        self.on_message = self._on_message
        self.on_log = self._on_log

        if self._config.mqtt.tls or self._config.mqtt.port == 8883:
            LOGGER.info(
                "%s Using TLS connection with TLS_CA_CERT: %s", LOG_PREFIX, TLS_CA_CERT
            )
            self.tls_set(
                ca_certs=TLS_CA_CERT,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLSv1_2,
            )

            self.tls_insecure_set(True)

    ##########################################
    def start(self):
        """Connect and start message loop"""
        LOGGER.info("%s Starting connector to Home-Assistant", LOG_PREFIX)
        self._tries = 0
        self._connected_event.clear()
        self._connect()
        self.loop_start()

    ##########################################
    def stop(self):
        """Stop message loop and disconnect"""
        LOGGER.info("%s Stopping message loop", LOG_PREFIX)
        self._tries = 0
        self.loop_stop()
        self.disconnect()
        LOGGER.info("%s Exit", LOG_PREFIX)

    ##########################################
    def _connect(self):
        """Connect to MQTT broker"""
        if not self._running.is_set():
            return

        self._tries += 1
        LOGGER.info(
            "%s Connecting to mqtt://%s:%s (attempt %s)",
            LOG_PREFIX,
            self._config.mqtt.host,
            self._config.mqtt.port,
            self._tries,
        )
        if self._tries > 2:
            time.sleep(5)

        self._connected_event.clear()
        try:
            self.connect(
                host=self._config.mqtt.host, port=self._config.mqtt.port, 
            )
        except socket.timeout as err:
            LOGGER.error("%s Failed to connect to MQTT broker. %s", LOG_PREFIX, err)
            self._connected = False
            self._connected_event.set()

        LOGGER.debug("%s Waiting for connect", LOG_PREFIX)

    ##########################################
    def connected(self):
        """Return bool for connection status"""
        return self._connected

    ##########################################
    def _on_connect(
        self, mqttc, userdata, flags, response_code
    ):  # pylint: disable=unused-argument, invalid-name
        """MQTT broker connect event"""
        if response_code == 0:
            self._connected = True
            LOGGER.info(
                "%s Connected mqtt://%s:%s",
                LOG_PREFIX,
                self._config.mqtt.host,
                self._config.mqtt.port,
            )

            for topic in self._subscribe:
                LOGGER.info("%s Subscribing to %s", LOG_PREFIX, topic)
                self.subscribe(topic, 0)

            self._connected_event.set()

        else:
            self._connected = False
            self._connected_event.clear()
            LOGGER.error(
                "%s Connection Failed. Error: %s",
                LOG_PREFIX,
                MQTT_CONN_CODES.get(response_code, "Unknown"),
            )

    ##########################################
    def _on_disconnect(
        self, mqttc, obj, response_code
    ):  # pylint: disable=unused-argument, invalid-name
        """MQTT broker was disconnected"""
        LOGGER.error(
            "%s Disconnected. response_code=%s %s",
            LOG_PREFIX,
            response_code,
            MQTT_CONN_CODES.get(response_code, "Unknown"),
        )

        self._connected = False
        self._connected_event.clear()
        if self._tries > 20:
            LOGGER.error("%s Failed to re-connect. Exit", LOG_PREFIX)
            self.stop()
            self._running.clear()

        elif self._tries > 15:
            LOGGER.info("%s [%s] Attempting re-connect.", LOG_PREFIX, self._tries)
            self.stop()
            self.setup()
            self.start()

    ##########################################
    def _on_log(self, mqttc, obj, level, string):  # pylint: disable=unused-argument
        """Log string from MQTT client"""
        LOGGER.info("%s [%s] %s",LOG_PREFIX, level, string)

    ##########################################
    def _on_message(
        self, mqttc, obj, msg
    ):  # pylint: disable=unused-argument, invalid-name
        """Call back function for recieved MQTT message"""
        LOGGER.debug("%s %s payload: %s", LOG_PREFIX, msg.topic, msg.payload)
        self._connected_event.set()
        if self._callback is not None:
            payload = str(msg.payload.decode("utf-8"))
            if payload[0] == "}":
                try:
                    payload = json.loads(payload)

                except json.JSONDecodeError as err:
                    LOGGER.error(
                        "%s Failed to decode JSON payload. %s", LOG_PREFIX, err
                    )
                    LOGGER.debug(payload)
                    return

            self._callback(
                {
                    TOPIC: msg.topic,
                    PAYLOAD: payload,
                    "qos": msg.qos,
                    "retain": msg.retain,
                }
            )

        else:
            LOGGER.error(
                "%s on_message callback is None. Set with obj.message_callback()",
                LOG_PREFIX,
            )

    ##########################################
    def set_callback(self, callback=None):
        """Set call back function for MQTT message"""
        self._callback = callback

    ##########################################
    def set_will(self, topic:str, payload:str):
        """Set exit() will message"""
        self.will_set(topic, payload=payload, qos=0, retain=False)

    ##########################################
    def _on_subscribe(
        self, mqttc, obj, mid, granted_qos
    ):  # pylint: disable=unused-argument
        """Call back function for subcribe to topic"""
        LOGGER.debug(
            "%s Subscribed to %s %s qos[{%s]",
            LOG_PREFIX,
            self._subscribe,
            mid,
            granted_qos[0],
        )

    ##########################################
    def subscribe_to(self, topic:str=None):
        """Add topic to subscribe"""
        if not topic:
            return
        LOGGER.debug("%s Subscribe to %s", LOG_PREFIX, topic)
        self._subscribe.append(topic)
        self.subscribe(topic, 0)

    ##########################################
    def pub(
        self,
        topic: str,
        payload: dict,
        qos: int = 1,
        retain: bool = False,
    )->bool:
        """Publish payload to MQTT topic"""
        if not self._running.is_set():
            return False

        if not self._connected:
            self._connect()

        if isinstance(payload, dict):
            payload = json.dumps(payload, default=str,)

        LOGGER.debug("%s publish: %s", LOG_PREFIX, topic)

        try:
            self.publish(topic, payload=payload, qos=qos, retain=retain)
            self._connected_event.set()

        except WebsocketConnectionError as err:
            LOGGER.error("%s Publish failed. %s", LOG_PREFIX, err)
            return False

        return True

    ##########################################
    def ping(self, topic: str, src: str)->bool:
        """Send ping message"""
        return self.pub(topic, {"ping": "request", "src": src})
