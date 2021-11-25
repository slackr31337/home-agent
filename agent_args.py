"""Function for parsing CLI arguments"""

import argparse


from _version import __version__
from const import APP_NAME

APP_VER = f"{APP_NAME} {__version__}"
########################################################
def parse_args(argv):
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description=APP_VER)

    parser.add_argument(
        "-c",
        "--config",
        dest="config",
        type=str,
        default="config.yaml",
        help="Set config.yaml file",
    )

    parser.add_argument(
        "-s", "--service", dest="service", action="store_true", help="Run as service"
    )

    parser.add_argument(
        "-d", "--debug", dest="debug", action="store_true", help="Turn on DEBUG logging"
    )

    parser.set_defaults(service=False)
    parser.set_defaults(debug=False)
    return parser.parse_args(argv)
