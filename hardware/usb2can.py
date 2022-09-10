"""
USB to CANbus
Automotive data
"""

import threading
import usb
import can


from service.log import LOGGER
from service.states import ThreadSafeDict
from config import Config

CAN_DEVICE = "can0"
CAN_BITRATE = 500000
CAN_BUS = "socketcan"
CAN_DEFAULTS = {"channel": CAN_DEVICE, "bus_type": CAN_BUS, "bitrate": CAN_BITRATE}
CAN_DEVICES = {
    0: {
        "name": "OpenMoko, Inc. Geschwister Schneider CAN adapter",
        "vendor": 0x1D50,
        "product": 0x606F,
        "bus": "gs_usb",
        "bitrate": 250000,
    }
}
SENSOR_MAP = {
    "locks": None,
    "door_driver": None,
    "door_passenger": None,
    "door_rear_driver": None,
    "door_rear_passenger": None,
    "engine_running": None,
}
CAN_IDS = {
    1201: {4: "engine_running"},
    1073: {5: "door_"},
    1074: {0: "locks"},
}
CAN_VALUES = {"1201:4:1": True, "1201:4:0": False}
LOG_PREFIX = "[CANbus]"
##########################################
class HWModule:
    """Module for CANbus logger"""

    name = "CANbus module"
    slug = "canbus"
    platform = ["linux"]
    hardware = "raspberrypi"
    sensors = []
    for key in SENSOR_MAP:
        sensors.append(f"{slug}_{key}")

    ##########################################
    def __init__(self, config: Config):
        LOGGER.debug("%s init", LOG_PREFIX)
        self._config = config
        self._state = ThreadSafeDict()
        self._stop_event = threading.Event()

        self._device = None
        self._available = False

        canbus = self._discover()
        self._start_receiver(canbus)
        self._available = True

    ##########################################
    def _discover(self):
        """Find CANbus device"""
        device = {}
        config = self._config.get(self.slug)
        for item in ["channel", "bus_type", "bitrate"]:

            value = None
            if config:
                value = config.get(item)

            if value is None:
                value = CAN_DEFAULTS.get(item)

            if value is not None:
                device[item] = value

        LOGGER.info("%s discover: %s", LOG_PREFIX, device)

        if device.get("bus_type") == "gs_usb":
            dev = usb.core.find(idVendor=0x1D50, idProduct=0x606F)
            canbus = can.Bus(  # pylint:disable=abstract-class-instantiated
                bustype="gs_usb",
                channel=dev.product,
                bus=dev.bus,
                address=dev.address,
                bitrate=device.get("bitrate"),
            )

        else:
            canbus = can.Bus(  # pylint:disable=abstract-class-instantiated
                channel=device.get("channel"),
                interface=device.get("bus_type"),
                bitrate=device.get("bitrate"),
            )

        self._device = device
        return canbus

    ##########################################
    def stop(self):
        """Stop canbus thread"""
        self._stop_event.set()

    ##########################################
    def available(self):
        """Return bool for available status"""
        return self._available

    ##########################################
    def get(self, item):
        """Return state for sensor"""

        LOGGER.debug("%s get: %s", LOG_PREFIX, item)
        value = self._get_state(item)
        LOGGER.debug("%s %s=%s", LOG_PREFIX, item, value)
        return value, None

    ##########################################
    def _start_receiver(self, canbus):
        """Start thread to receive data from CANbus"""
        LOGGER.debug("%s Starting CANbus worker thread", LOG_PREFIX)
        self._receiver = threading.Thread(
            target=receiver,
            daemon=True,
            name=self.slug,
            args=(
                canbus,
                self._stop_event,
                self._save_state,
            ),
        )
        self._receiver.start()

    ##########################################
    def _get_state(self, key: str):
        """Get value from state dict"""
        value = None
        with self._state as _state:
            value = _state.get(key)
        return value

    ##########################################
    def _save_state(self, **kwargs):
        """Save data in dict"""
        with self._state as _state:
            for key, value in kwargs.items():
                if value is not None:
                    _state[key] = value


##########################################
def receiver(canbus: can.Bus, stop_event: threading.Event, call_back):
    """Receive message from CANbus"""
    try:
        LOGGER.debug("%s Starting receiver", LOG_PREFIX)
        with canbus as _bus:

            # can_filters = [{"can_id": 1, "can_mask": 0xF, }]
            # _bus.set_filters(can_filters,)

            while not stop_event.is_set():
                _msg = _bus.recv(timeout=1.0 / 1000.0)
                if _msg is not None:
                    data = process_msg(_msg)
                    if data:
                        call_back(data)

    except (TypeError, can.CanInitializationError) as err:
        LOGGER.error("%s Exception %s", LOG_PREFIX, err)
        return

    LOGGER.info("%s receiver exit", LOG_PREFIX)


##########################################
def process_msg(_msg: can.Message) -> dict:
    """Process CAN message"""

    data = {}

    if _msg.arbitration_id in CAN_IDS:
        _msg_id = "0x{0:0{1}X}".format(  # pylint: disable=consider-using-f-string
            _msg.arbitration_id,
            8 if _msg.is_extended_id else 3,
        )
        print_packet(_msg_id, _msg)

        value = None
        value_map = CAN_IDS.get(_msg.arbitration_id)
        for _bit in value_map:
            key = f"{_msg.arbitration_id}:{_bit}:{value}"
            value = CAN_VALUES.get(key)
            if value is None:
                value = _msg.data[_bit]

            LOGGER.debug("%s %s key[%s] [%s]=%s", LOG_PREFIX, _msg_id, key, _bit, value)

    return data


##########################################
def print_packet(_msg_id, _msg: can.Message):
    """Format data in readable output"""

    _id = str(_msg.arbitration_id).rjust(4, "0")

    data = f"Packet:    [{_id}] {_msg_id}"
    for idx, _byte in enumerate(_msg.data):  # pylint: disable=unused-variable
        data += f" {_byte:02X}"

    print(data)
