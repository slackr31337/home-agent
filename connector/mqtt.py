"""Class for MQTT messaging"""

import ssl
import json
import time
import platform
import socket
import paho.mqtt.client as mqtt


from utilities.log import LOGGER
from const import TOPIC, PAYLOAD

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
LOG_PREFIX = "[MQTT]"
##########################################
class Connector(mqtt.Client):
    """Home Assistant Connector class"""

    name = "mqtt"

    ##########################################
    def __init__(
        self,
        config,
        event,
        running,
        clientid,
        **kwargs,
    ):

        super(Connector, self).__init__(clientid, **kwargs)
        self._connected_event = event
        self._running = running
        self._config = config
        self._connected = False
        self._callback = None
        self._tries = 0
        self._subscribe = []

        if clientid is None:
            self._clientid = f"mqtt_client_{int(time.time())}"
        else:
            self._clientid = clientid

        self.setup()

    ##########################################
    def start(self):
        """Connect and start message loop"""
        LOGGER.info("%s Starting connector to Home-Assistant", LOG_PREFIX)
        self._tries = 0
        self._connected_event.clear()
        self.connect()
        self._mqttc.loop_start()

    ##########################################
    def stop(self):
        """Stop message loop and disconnect"""
        LOGGER.info("%s Stopping message loop", LOG_PREFIX)
        self._tries = 0
        self._mqttc.loop_stop()
        self._mqttc.disconnect()
        LOGGER.info("%s Exit", LOG_PREFIX)

    ##########################################
    def setup(self):
        """Setup MQTT client"""
        LOGGER.info("%s Setup MQTT client %s", LOG_PREFIX, self._clientid)
        self._mqttc = mqtt.Client(
            client_id=self._clientid,
            clean_session=True,
        )

        if self._config.mqtt.port == 8883:
            LOGGER.info(
                "%s Using TLS connection with TLS_CA_CERT: %s", LOG_PREFIX, TLS_CA_CERT
            )
            self._mqttc.tls_set(
                ca_certs=TLS_CA_CERT,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLSv1_2,
            )

            self._mqttc.tls_insecure_set(True)

        self._mqttc.username_pw_set(
            username=self._config.mqtt.user, password=self._config.mqtt.password
        )
        self._mqttc.reconnect_delay_set(min_delay=3, max_delay=30)
        self._mqttc.on_connect = self.mqtt_on_connect
        self._mqttc.on_disconnect = self.mqtt_on_disconnect
        self._mqttc.on_subscribe = self.mqtt_on_subscribe
        self._mqttc.on_message = self.mqtt_on_message

    ##########################################
    def connect(self):
        """Connect to MQTT broker"""
        if not self._running.is_set():
            return

        self._tries += 1
        LOGGER.info(
            "%s Connecting to %s:%s (attempt %s)",
            LOG_PREFIX,
            self._config.mqtt.host,
            self._config.mqtt.port,
            self._tries,
        )
        try:
            self._mqttc.connect(
                host=self._config.mqtt.host, port=self._config.mqtt.port
            )
        except socket.timeout as err:
            LOGGER.error("%s Failed to connect to MQTT broker. %s", LOG_PREFIX, err)
            self._connected = False
            self._connected_event.set()

    ##########################################
    def connected(self):
        """Return bool for connection status"""
        return self._connected

    ##########################################
    def mqtt_on_connect(
        self, mqttc, userdata, flags, rc
    ):  # pylint: disable=unused-argument, invalid-name
        """MQTT broker connect event"""
        if rc == 0:
            self._connected = True
            LOGGER.info(
                "%s Connected mqtt://%s:%s",
                LOG_PREFIX,
                self._config.mqtt.host,
                self._config.mqtt.port,
            )

            for topic in self._subscribe:
                LOGGER.info("%s Subscribing to %s", LOG_PREFIX, topic)
                self._mqttc.subscribe(topic, 0)

            self._connected_event.set()
        else:
            self._connected = False
            self._connected_event.clear()
            LOGGER.error(
                "%s Connection Failed. Error: %s",
                LOG_PREFIX,
                MQTT_CONN_CODES.get(rc, "Unknown"),
            )

    ##########################################
    def mqtt_on_disconnect(
        self, mqttc, obj, rc
    ):  # pylint: disable=unused-argument, invalid-name
        """MQTT broker was disconnected"""
        LOGGER.error(
            "%s Disconnected. rc=%s %s",
            LOG_PREFIX,
            rc,
            MQTT_CONN_CODES.get(rc, "Unknown"),
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
    def mqtt_log(self, mqttc, obj, level, string):  # pylint: disable=unused-argument
        """Log string from MQTT client"""
        LOGGER.debug("%s %s", string)

    ##########################################
    def mqtt_on_message(
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
    def message_callback(self, callback=None):
        """Set call back function for MQTT message"""
        self._callback = callback

    ##########################################
    def set_will(self, topic, payload):
        """Set exit() will message"""
        self._mqttc.will_set(topic, payload=payload, qos=0, retain=False)

    ##########################################
    def mqtt_on_subscribe(
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
    def subscribe_to(self, topic=None):
        """Add topic to subscribe"""
        LOGGER.debug("%s Subscribe to %s", LOG_PREFIX, topic)
        self._subscribe.append(topic)
        self._mqttc.subscribe(topic, 0)

    ##########################################
    def publish(self, _topic, payload, qos=1, retain=False):
        """Publish payload to MQTT topic"""
        if not self._running.is_set():
            return False

        if not self._connected:
            self.connect()

        if isinstance(payload, dict):
            payload = json.dumps(payload, default=str)

        LOGGER.debug("%s publish: %s", LOG_PREFIX, _topic)

        try:
            result = self._mqttc.publish(
                _topic, payload=payload, qos=qos, retain=retain
            )
            result.wait_for_publish(timeout=5)
            if result.is_published():
                self._connected_event.set()

        except mqtt.WebsocketConnectionError as err:
            LOGGER.error("%s Publish failed. %s", LOG_PREFIX, err)
            return False

        return True

    ##########################################
    def ping(self, topic: str, src: str):
        """Send ping message"""
        self.publish(topic, {"ping": "request", "src": src})
