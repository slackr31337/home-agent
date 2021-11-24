"""Function for parsing CLI arguments"""

import argparse


from _version import __version__
from const import APP_NAME
from config import (
    DEFAULT_CONNECTOR,
    API_URL,
    API_TOKEN,
    MQTT_HOST,
    MQTT_PORT,
    MQTT_USER,
    MQTT_PASS,
    EVENT_LOOP_DELTA,
    METRICS_DELTA,
)

APP_VER = f"{APP_NAME} {__version__}"
########################################################
def parse_args(argv):
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description=APP_VER)

    parser.add_argument(
        "-s", "--service", dest="service", action="store_true", help="Run as service"
    )
    parser.add_argument(
        "-c",
        "--connector",
        dest="connector",
        type=str,
        default="mqtt",
        help=f'Set Home Assistant connector. Use "mqtt" or "api" (Default: {DEFAULT_CONNECTOR})',
    )

    parser.add_argument(
        "-u",
        "--api-url",
        dest="api_url",
        type=str,
        default=API_URL,
        help="Set Home Assistant API url",
    )

    parser.add_argument(
        "-t",
        "--api-token",
        dest="api_token",
        type=str,
        default=API_TOKEN,
        help="Set Home Assistant API Long-Lived Access Token",
    )

    parser.add_argument(
        "-mh",
        "--mqtt-host",
        dest="mqtt_host",
        type=str,
        default=MQTT_HOST,
        help=f"Set MQTT broker host (default: {MQTT_HOST})",
    )

    parser.add_argument(
        "-mp",
        "--mqtt-port",
        dest="mqtt_port",
        type=int,
        default=MQTT_PORT,
        help=f"Set MQTT broker port (default: {MQTT_PORT})",
    )

    parser.add_argument(
        "--mqtt-user",
        dest="mqtt_user",
        type=str,
        default=MQTT_USER,
        help="Set MQTT broker user name",
    )

    parser.add_argument(
        "--mqtt-pass",
        dest="mqtt_pass",
        type=str,
        default=MQTT_PASS,
        help="Set MQTT broker user password",
    )

    parser.add_argument(
        "-ei",
        "--events-interval",
        dest="events_interval",
        type=int,
        default=EVENT_LOOP_DELTA,
        help=f"Set the publish events interval (default {EVENT_LOOP_DELTA}s",
    )

    parser.add_argument(
        "-mi",
        "--metrics-interval",
        dest="metrics_interval",
        type=int,
        default=METRICS_DELTA,
        help=f"Set the metrics publish interval (default: {METRICS_DELTA}s",
    )

    parser.add_argument(
        "-p",
        "--poll-modules",
        dest="modules_interval",
        type=int,
        default=10,
        help=f"Set the metrics publish interval (default: 10s",
    )

    parser.add_argument(
        "-d", "--debug", dest="debug", action="store_true", help="Turn on DEBUG logging"
    )

    parser.set_defaults(service=False)
    parser.set_defaults(disable_mqtt=False)
    parser.set_defaults(debug=False)
    return parser.parse_args(argv)
