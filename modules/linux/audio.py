"""
Audio module for Linux
pyalsaaudio
apt-get install libasound2-dev
"""
# pyalsaaudio; sys_platform == 'linux'

try:
    import alsaaudio

except ImportError:
    raise ImportError(  # pylint: disable=raise-missing-from
        "Unable to import alsaaudio. Please run sudo apt install -y libasound2-dev && python3 -m pip install pyalsaaudio"
    )

from service.log import LOGGER

MUTE_MAP = {"ON": 1, "OFF": 0}
STATE_MAP = {1: "ON", 0: "OFF"}
LOG_PREFIX = r"[Audio]"
###########################################
class AgentModule:
    """Class for audio device support"""

    name = "Audio module"
    slug = "audio"
    platform = ["linux"]
    _available = False
    sensors = ["audio_volume", "audio_mute", "audio_mixer"]
    attribs = {}
    sensors_set = ["audio_volume", "audio_mute"]
    sensor_types = {
        "audio_mute": "switch",
    }
    sensor_attribs = {
        "switch": {
            "topic": "~/state",
            "value_template": "{{ value_json.state }}",
            "json_attributes_topic": "~/attrib",
            "command_topic": "~/set",
        },
    }
    sensor_class = {"audio_volume": {"unit_of_measurement": "%"}}
    sensor_icons = {
        "audio_volume": "volume-high",
        "audio_mute": "volume-off",
        "audio_mixer": "tune-vertical",
    }

    services = {}

    ##########################################
    def __init__(self, config: dict):
        self._config = config
        self._available = False
        self._card = None
        self._channel = None
        self._mixer = None
        self._setup()

    ##########################################
    def _setup(self):
        """Setup module"""
        LOGGER.info(
            "%s Setup audio card and mixer",
            LOG_PREFIX,
        )
        for idx in alsaaudio.card_indexes():
            (name, longname) = alsaaudio.card_name(  # pylint: disable=unused-variable
                idx
            )
            LOGGER.info("%s Card[%s] %s", LOG_PREFIX, idx, name)

        for name in alsaaudio.mixers():
            mixer = alsaaudio.Mixer(name)
            LOGGER.info("%s Mixer %s", LOG_PREFIX, name)
            volumes = mixer.getvolume()
            for idx in range(len(volumes)):
                LOGGER.info("%s Channel %s: volume: %s", LOG_PREFIX, idx, volumes[idx])

        self._channel = alsaaudio.mixers()[0]
        try:
            self._mixer = alsaaudio.Mixer(self._channel)

        except alsaaudio.ALSAAudioError:
            LOGGER.error("%s Mixer not found [%s]", LOG_PREFIX, self._channel)
            return

        self._card = self._mixer.mixer()
        LOGGER.info("%s Setup: %s", LOG_PREFIX, self._card)

        self._available = True

    ##########################################
    def available(self):
        """Return bool for available status"""
        return self._available

    ##########################################
    def get(self, item: str):
        """Get sensor value"""

        attrib = {"mixer": self._card}
        value = None
        if item.endswith("volume"):
            volume = self._mixer.getvolume()
            idx = 0
            for item in volume:
                idx += 1
                attrib[f"channel{idx}"] = item

            value = int(volume[0])

        elif item.endswith("mixer"):
            value = self._mixer.mixer()
            attrib = {}

        elif item.endswith("mute"):
            mute = self._mixer.getmute()[0]
            value = STATE_MAP.get(mute)

        LOGGER.debug("%s get %s=%s", LOG_PREFIX, item, value)
        return value, attrib

    ##########################################
    def set(self, item: str, value):
        """Set mixer value"""
        LOGGER.debug("%s set %s=%s", LOG_PREFIX, item, value)
        if item.endswith("volume"):
            self._mixer.setvolume(int(value))

        elif item.endswith("mute"):
            self._mixer.setmute(MUTE_MAP.get(value))

        return value
