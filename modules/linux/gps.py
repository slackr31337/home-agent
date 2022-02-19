"""Class for gpsd client"""

import os
from threading import Thread
from datetime import datetime
from serial import Serial
from pynmeagps import NMEAReader
import pynmeagps.exceptions as nme


from utilities.log import LOGGER
from utilities.states import ThreadSafeDict

LOG_PREFIX = "[GPS]"
STATE_MAP = {}
################################################################
class AgentModule:

    name = "GPS module"
    slug = "gps"
    platform = ["linux"]
    sensors = ["location"]
    attribs = {}
    sensor_types = {}
    sensor_attribs = {}
    sensor_class = {}
    sensor_icons = {}
    sensors_set = []
    services = {}
    gps_dev = "/dev/ttyUSB1"

    ###############################################################
    def __init__(self):
        self._location = Location(self.gps_dev)
        if not self._location.ready():
            return
        self._available = True
        self._worker = Thread(
            target=self._location.start, daemon=True, name="GPS Worker", args=()
        )
        self._worker.start()

    ###############################################################
    def stop(self):
        """Stop GPS worker thread"""
        self._location.stop()
        if self._worker:
            self._worker.join(1)

    ###############################################################
    def available(self):
        return self._available

    ###############################################################
    def get(self, _method):
        """Return state for given method"""
        LOGGER.debug("%s get: %s", LOG_PREFIX, _method)

        if hasattr(self, _method):
            _func = getattr(self, _method)
            LOGGER.debug("%s module function: %s()", LOG_PREFIX, _func.__name__)
            return _func()

        # value, attribs = self._state.get(_method)
        # if value in STATE_MAP:
        #    value = STATE_MAP.get(value)

        # LOGGER.debug("%s module sensor %s %s", LOG_PREFIX, _method, value)
        # return value, attribs

    ###############################################################
    def location(self):
        location = self._location.get_location()
        LOGGER.info("%s location: %s", LOG_PREFIX, location)
        return location.get("fix"), location


##########################################
class Location:
    """Gather GPS location data and store in state dict"""

    ##########################################
    def __init__(self, device, speed=4800):
        self._tty = device
        self._speed = speed
        self._running = False
        self._ready = False
        self._count = 0
        self._state = ThreadSafeDict()
        if not os.path.exists(device):
            LOGGER.error("%s Unable to open gps device: %s", LOG_PREFIX, device)
            return
        self.stream = Serial(self._tty, speed, timeout=1)
        self.nmea = NMEAReader(self.stream)
        self._ready = True

    ##########################################
    def start(self):
        """Setup TTY and open for GPS data"""
        self._running = True
        self._read_data()

    ##########################################
    def stop(self):
        """Stop data loop"""
        self._running = False

    ##########################################
    def ready(self):
        """Rrturn bool"""
        return self._ready

    ##########################################
    def _read_data(self):
        """Loop to read GPS data from TTY"""
        while self._running:
            try:
                for (_, msg) in self.nmea:  # invokes iterator method
                    if msg.msgID == "GGA":
                        dat = datetime.now()
                        tim = msg.time
                        # dat = (
                        #    dat.replace(
                        #        year=dat.year,
                        #        month=dat.month,
                        #        day=dat.day,
                        #        hour=tim.hour,
                        #        minute=tim.minute,
                        #        second=tim.second,
                        #    ).isoformat()
                        #    + "Z"
                        # )
                        if msg.quality == 1:
                            fix = "3d"

                        elif msg.quality == 2:
                            fix = "2d"

                        else:
                            fix = "none"

                        self._save_state(
                            time=tim,
                            lat=msg.lat,
                            lon=msg.lon,
                            alt=msg.alt,
                            fix=fix,
                            hdop=msg.HDOP,
                        )
                        self._count += 1

            except (nme.NMEAMessageError, nme.NMEATypeError, nme.NMEAParseError) as err:
                # print(f"Error {err}")
                continue

    ##########################################
    def _save_state(self, **kwargs):
        """Save GPS data to dict"""
        with self._state as _state:
            for key, value in kwargs.items():
                if value is not None:
                    _state[key] = value

    ##########################################
    def get_location(self):
        """Return dict with location data"""

        with self._state as _state:
            data = _state.copy()
        return data
