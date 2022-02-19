"""Class for gathering Raspberry Pi hardware info"""
##########################################
class RaspberryPi:

    _manufacturer = "Raspberry Pi"
    _firmware = ""
    machine = "arm"

    def __init__(self):
        self.get_hardware()

    def get_hardware(self):
        """Fetch Raspberry Pi Hardware info"""
        keys = {
            "serial": "/proc/device-tree/serial-number",
            "model": "/proc/device-tree/model",
        }
        for key, path in keys.items():
            with open(path) as file:
                value = file.readline()
            setattr(self, f"_{key}", str(value))

    def manufacturer(self):
        """Return str"""
        return self._manufacturer

    def model(self):
        """Return str"""
        return self._model.split(self._manufacturer)[1]

    def serial_number(self):
        """Return str"""
        return self._serial

    def firmware(self):
        """Return str"""
        return self._firmware

    def processor(self):
        """Return str"""
        return self._processor