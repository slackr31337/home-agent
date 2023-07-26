"""Class for gpsd client"""

import os
import time
import threading
import serial
from pynmeagps import NMEAReader
import pynmeagps.exceptions as nme


from service.log import LOGGER
from service.states import ThreadSafeDict
from config import Config

LOG_PREFIX = "[GPS]"
STATE_MAP = {}


##########################################
class AgentModule:
    """Agent class for GPS"""

    name = "GPS module"
    slug = "gps"
    platform = ["linux"]
    sensors = ["location"]
    attribs = {}
    sensor_icons = {"location": "satellite-variant"}
    _available = False

    ##########################################
    def __init__(self, config: Config):
        self._config = config.get("gps")
        self._dev = self._config.get("dev")

        LOGGER.info("%s init using: %s", LOG_PREFIX, self._dev)
        self._ready = threading.Event()
        self._ready.clear()
        self._location = Location(self._ready, self._dev)
        if not self._location.ready():
            return

        self._available = True
        self._worker = threading.Thread(
            target=self._location.start, daemon=True, name="GPS Worker", args=()
        )
        self._worker.start()

    ##########################################
    def stop(self):
        """Stop GPS worker thread"""

        self._ready.clear()
        self._location.stop()
        if self._worker:
            self._worker.join(1)

    ##########################################
    def available(self):
        """Return bool for module available"""

        return self._available

    ##########################################
    def get(self, item):
        """Return state for given method"""
        # LOGGER.debug("%s get: %s", LOG_PREFIX, item)

        if hasattr(self, item):
            _func = getattr(self, item)
            LOGGER.debug("%s module function: %s()", LOG_PREFIX, _func.__name__)
            return _func()

        location = self._location.state()
        value = location.get(item)
        LOGGER.debug("%s get: %s value: %s", LOG_PREFIX, item, value)
        return value, None

    ##########################################
    def location(self):
        """Get location and fix"""

        location = self._location.state()
        return location.get("fix"), location


##########################################
class Location:
    """Gather GPS location data and store in state dict"""

    ##########################################
    def __init__(self, ready, device, speed=4800):
        self._metric = False
        self._ready = ready
        self._tty = device
        self._speed = speed
        self._running = False
        self._count = 0
        self._state = ThreadSafeDict()
        self._serial = serial.Serial(self._tty, speed, timeout=5)
        self._nmea = NMEAReader(self._serial)
        self._serial_open()

    ##########################################
    def start(self):
        """Setup TTY and open for GPS data"""
        LOGGER.debug("%s Start NMEA reader", LOG_PREFIX)
        self._running = True
        self._read_data()

    ##########################################
    def ready(self):
        """Return bool"""

        return self._ready.is_set()

    ##########################################
    def stop(self):
        """Stop data loop"""

        self._running = False

    ##########################################
    def _serial_open(self):
        """Open serial device for reading"""

        LOGGER.debug("%s Open serial port: %s", LOG_PREFIX, self._tty)

        self._ready.clear()
        self._nmea = None
        if not self._tty or not os.path.exists(self._tty):
            LOGGER.error("%s Unable to open gps device: %s", LOG_PREFIX, self._tty)
            time.sleep(0.3)
            self._serial.close()
            return

        if self._serial.isOpen():
            try:
                LOGGER.debug("%s Closing serial port", LOG_PREFIX)
                self._serial.close()
                LOGGER.debug("%s Reopen serial port", LOG_PREFIX)
                self._serial.open()

            except serial.serialutil.SerialException as err:
                LOGGER.error("%s Exception %s", LOG_PREFIX, err)

        LOGGER.info("%s Setup NMEA reader", LOG_PREFIX)
        self._nmea = NMEAReader(self._serial)
        self._ready.set()
        LOGGER.info("%s Ready", LOG_PREFIX)

    ##########################################
    def _read_data(self):
        """Loop to read GPS data from TTY"""

        LOGGER.debug("%s read GPS data", LOG_PREFIX)

        while self._running:
            error = None
            if not self._serial.isOpen():
                error = "Serial port is closed"
                self._ready.wait(15)
                self._serial_open()

            if not self._nmea:
                LOGGER.error("%s NMEA reader not found", LOG_PREFIX)
                continue

            try:
                for _, msg in self._nmea:
                    if msg.msgID == "GGA":
                        self._process_gga(msg)
                        self._count += 1

                    elif msg.msgID == "VTG":
                        self._process_vtg(msg)
                        self._count += 1

            except (nme.NMEAMessageError, nme.NMEATypeError, nme.NMEAParseError) as err:
                error = f"Exception {err}"

            except serial.SerialException as err:
                error = f"Exception {err}"
                self._serial.close()

            if error:
                LOGGER.error("%s %s", LOG_PREFIX, error)

        self._nmea = None
        self._serial.close()
        self._serial = None
        LOGGER.info("%s Exit NMEA reader", LOG_PREFIX)

    ##########################################
    def _process_gga(self, msg):
        """Process NMEA GPGGA message"""

        if msg.quality == 1:
            fix = "3D Fix"

        elif msg.quality == 2:
            fix = "2D Fix"

        else:
            fix = "No fix"
            self._save_state(fix=fix, sats=msg.numSV)
            return

        altitude = msg.alt
        gps_accuracy = float(msg.HDOP * 2.5)
        if not self._metric:
            altitude = float(altitude * 3.281)
            gps_accuracy = float(gps_accuracy * 3.281)

        self._save_state(
            latitude=msg.lat,
            longitude=msg.lon,
            altitude=altitude,
            fix=fix,
            gps_accuracy=gps_accuracy,
            sats=msg.numSV,
        )

    ##########################################
    def _process_vtg(self, msg):
        """Process NMEA GPVTG message"""

        speed = str(msg.sogk)
        if len(speed) == 0:
            return
        speed = float(speed)
        if not self._metric:
            speed = f"{float(speed / 1.609):.1f}"

        self._save_state(speed=float(speed), course=msg.cogt)

    ##########################################
    def _save_state(self, **kwargs):
        """Save GPS data to dict"""

        with self._state as _state:
            for key, value in kwargs.items():
                if value is not None:
                    _state[key] = value

    ##########################################
    def state(self):
        """Return dict with location data"""

        with self._state as _state:
            data = _state.copy()

        return data
