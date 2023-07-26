"""Class for gathering Raspberry Pi hardware info"""


##########################################
class RaspberryPi:
    """Class for Raspberry Pi Hardware"""

    platform = ["linux"]
    hardware = "raspberrypi"
    machine = "arm"
    _manufacturer = "Raspberry Pi"
    _firmware = ""
    _model = ""
    _serial = ""
    _processor = ""

    ##########################################
    def __init__(self):
        self.get_hardware()

    ##########################################
    def get_hardware(self):
        """Fetch Raspberry Pi Hardware info"""

        keys = {
            "serial": "/proc/device-tree/serial-number",
            "model": "/proc/device-tree/model",
        }
        for key, path in keys.items():
            with open(path, encoding="utf-8") as file:
                value = file.read()
                value = str(value).rstrip(" \t\r\n\0")

            setattr(self, f"_{key}", value)

    ##########################################
    def manufacturer(self):
        """Return str"""

        return self._manufacturer

    ##########################################
    def model(self):
        """Return str"""

        return str(self._model.split(self._manufacturer)[1]).strip()

    ##########################################
    def serial_number(self):
        """Return str"""

        return self._serial

    ##########################################
    def firmware(self):
        """Return str"""

        return self._firmware

    ##########################################
    def processor(self):
        """Return str"""

        return self._processor
