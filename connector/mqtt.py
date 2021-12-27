"""Class for MQTT messaging"""
import ssl
import json
import time
import platform
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
        self._connected = False
        self._callback = None
        self._tries = 0
        self._subscribe = []

        self._host = config.mqtt.host
        self._port = config.mqtt.port

        if clientid is None:
            self._clientid = f"mqtt_client_{int(time.time())}"
        else:
            self._clientid = clientid

        self._mqttc = mqtt.Client(
            client_id=self._clientid,
            clean_session=True,
        )

        if self._port == 8883:
            self._mqttc.tls_set(
                ca_certs=TLS_CA_CERT,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLSv1_2,
            )

            self._mqttc.tls_insecure_set(True)

        self._mqttc.username_pw_set(
            username=config.mqtt.user, password=config.mqtt.password
        )
        self._mqttc.reconnect_delay_set(min_delay=1, max_delay=30)
        self._mqttc.on_connect = self.mqtt_on_connect
        self._mqttc.on_disconnect = self.mqtt_on_disconnect
        self._mqttc.on_subscribe = self.mqtt_on_subscribe
        self._mqttc.on_message = self.mqtt_on_message

    ##########################################
    def mqtt_log(self, mqttc, obj, level, string):
        LOGGER.debug("%s %s", string)

    ##########################################
    def connect(self):
        if not self._running.is_set():
            LOGGER.error("%s Running is not set", LOG_PREFIX)
            return
        LOGGER.info(
            "%s [%s] connecting to %s:%s",
            LOG_PREFIX,
            self._tries,
            self._host,
            self._port,
        )
        self._tries += 1
        if self._tries > 10:
            LOGGER.error("%s Failed to connect to MQTT broker", LOG_PREFIX)
            raise Exception("Failed to connect")

        self._mqttc.connect(host=self._host, port=self._port, keepalive=60)

    ##########################################
    def connected(self):
        return self._connected

    ##########################################
    def start(self):
        LOGGER.info("%s Starting message loop", LOG_PREFIX)
        self._tries = 0
        if not self._connected:
            LOGGER.info("%s Connecting", LOG_PREFIX)
            self.connect()

        for _topic in self._subscribe:
            LOGGER.info("%s Subscribing to %s", LOG_PREFIX, _topic)
            self._mqttc.subscribe(_topic, 0)

        self._mqttc.loop_start()

    ##########################################
    def stop(self):
        LOGGER.info("%s Stopping message loop")
        self._mqttc.loop_stop()
        self._mqttc.disconnect()

    ##########################################
    def mqtt_on_connect(self, mqttc, userdata, flags, rc):
        """MQTT broker connect event"""
        if rc == 0:
            self._connected = True
            LOGGER.info("%s Connected mqtt://%s:%s", LOG_PREFIX, self._host, self._port)
            self._connected_event.set()
        else:
            self._connected = False
            self._connected_event.clear()
            LOGGER.error(
                "%s Connection Failed. %s", LOG_PREFIX, MQTT_CONN_CODES.get(rc)
            )

    ##########################################
    def mqtt_on_disconnect(self, mqttc, obj, rc):
        """MQTT broker was disconnected"""
        LOGGER.error(
            "%s Disconnected. rc=%s %s", LOG_PREFIX, rc, MQTT_CONN_CODES.get(rc)
        )
        self._connected = False
        self._connected_event.clear()
        self.connect()

    ##########################################
    def mqtt_on_message(self, mqttc, obj, msg):
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
    def message_callback(self, callback):
        self._callback = callback

    ##########################################
    def set_will(self, topic, payload):
        """Set exit() will message"""
        self._mqttc.will_set(topic, payload=payload, qos=0, retain=False)

    ##########################################
    def mqtt_on_subscribe(self, mqttc, obj, mid, granted_qos):
        LOGGER.debug(
            "%s Subscribed to %s %s qos[{%s]",
            LOG_PREFIX,
            self._subscribe,
            mid,
            granted_qos[0],
        )

    ##########################################
    def subscribe_to(self, _topic=None):
        self._subscribe.append(_topic)
        if self.connected:
            self._mqttc.subscribe(_topic, 0)

    ##########################################
    def publish(self, _topic, payload, qos=1, retain=False):
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
    def ping(self, topic):
        """Send ping message"""
        self.publish(topic, "ping")
