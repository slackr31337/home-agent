"""Function for parsing CLI arguments"""

import argparse


########################################################
def parse_args(argv: list, app_name: str) -> dict:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(description=app_name)

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
    return vars(parser.parse_args(argv))
