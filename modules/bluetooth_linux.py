"""Class to scan for bluetooth devices"""


LOG_PREFIX = "[bluetooth_linux]"
#########################################
class agent_module:

    name = "Bluetooth module"
    slug = "bluetooth_linux"
    platform = ["linux"]
    services = {}
    sensors = ["bluetooth"]
    sensors_set = ["disable_scan"]
    sensor_types = {
        "bluetooth": "sensor",
        "disable_scan": "switch",
    }
    sensor_attribs = {
        "switch": {
            "topic": "~/state",
            "value_template": "{{ value_json.state }}",
            "json_attributes_topic": "~/attrib",
            "command_topic": "~/set",
        },
    }
