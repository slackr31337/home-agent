"""Class for MQTT messaging"""
import ssl
import json
import time
import paho.mqtt.client as mqtt


from log import LOGGER
from const import TOPIC, PAYLOAD

TLS_CA_PATH = "/etc/ssl/certs/"
TLS_CA_CERT = "/etc/ssl/certs/ca-certificates.crt"
TLS_CERT = "/etc/ssl/private/mqtt_client.crt"
TLS_KEY = "/etc/ssl/private/mqtt_client.key"

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
#########################################
class Connector(mqtt.Client):

    name = "mqtt"

    #########################################
    def __init__(
        self,
        _config,
        _connected,
        clientid,
        **kwargs,
    ):

        super(Connector, self).__init__(clientid, **kwargs)
        self._connected_event = _connected
        self.disconnected = None
        self._connected = False
        self._callback = None
        self._subscribe = []

        self._host = _config.mqtt.host
        self._port = _config.mqtt.port

        if clientid is None:
            clientid = f"mqtt_client_{int(time.time())}"

        self._mqttc = mqtt.Client(
            client_id=clientid,
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
            username=_config.mqtt.user, password=_config.mqtt.password
        )
        self._mqttc.on_connect = self.mqtt_on_connect
        self._mqttc.on_disconnect = self.mqtt_on_disconnect
        self._mqttc.on_subscribe = self.mqtt_on_subscribe
        self._mqttc.on_message = self.mqtt_on_message

    #########################################
    def mqtt_log(self, mqttc, obj, level, string):
        LOGGER.debug("[MQTT] %s", string)

    #########################################
    def mqtt_on_connect(self, mqttc, userdata, flags, rc):
        """MQTT broker connect event"""
        if rc == 0:
            self._connected = True
            LOGGER.info("[MQTT] Connected mqtt://%s:%s", self._host, self._port)
            self._connected_event.set()
        else:
            self._connected = False
            self._connected_event.clear()
            LOGGER.error("[MQTT] Connection Failed. %s", MQTT_CONN_CODES.get(rc))

    #########################################
    def mqtt_on_disconnect(self, mqttc, obj, rc):
        """MQTT broker was disconnected"""
        self._connected = False
        self.disconnected = True, rc
        self._connected_event.clear()

    #########################################
    def mqtt_on_message(self, mqttc, obj, msg):
        LOGGER.debug("[MQTT] %s payload: %s", msg.topic, msg.payload)
        if self._callback is not None:
            payload = str(msg.payload.decode("utf-8"))
            if payload[0] == "}":
                try:
                    payload = json.loads(payload)

                except json.JSONDecodeError as err:
                    LOGGER.error("Failed to decode JSON payload. %s", err)
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
                "[MQTT] on_message callback is None. Set with obj.message_callback()"
            )

    #########################################
    def message_callback(self, callback):
        self._callback = callback

    #########################################
    def mqtt_on_subscribe(self, mqttc, obj, mid, granted_qos):
        LOGGER.debug(
            "[MQTT] Subscribed to %s %s qos[{%s]",
            self._subscribe,
            mid,
            granted_qos[0],
        )

    #########################################
    def subscribe_to(self, _topic=None):
        self._subscribe.append(_topic)
        if self.connected:
            self._mqttc.subscribe(_topic, 0)

    #########################################
    def connect(self):
        LOGGER.info("[MQTT] connecting to %s:%s", self._host, self._port)
        self._mqttc.connect(self._host, self._port, 60)

    #########################################
    def connected(self):
        return self._connected

    #########################################
    def start(self):
        LOGGER.info("[MQTT] Starting message loop")

        if not self._connected:
            self.connect()

        for _topic in self._subscribe:
            LOGGER.info("[MQTT] Subscribing to %s", _topic)
            self._mqttc.subscribe(_topic, 0)

        return self._mqttc.loop_start()

    #########################################
    def stop(self):
        LOGGER.info("[MQTT] Stopping message loop")
        self._mqttc.loop_stop()
        self._mqttc.disconnect()

    #########################################
    def publish(self, _topic, payload, qos=1, retain=False):
        if not self._connected:
            self.connect()

        if isinstance(payload, dict):
            payload = json.dumps(payload, default=str)
        LOGGER.debug("%s publish: %s", LOG_PREFIX, _topic)
        return self._mqttc.publish(_topic, payload=payload, qos=qos, retain=retain)

    #########################################
    def ping(self, topic):
        """Send ping message"""
        self.publish(topic, "ping")
