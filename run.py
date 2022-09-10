#!/usr/bin/env python3
"""Run the HomeAgent as a service"""

from distutils.debug import DEBUG
import sys
import threading
import traceback
import logging



from service.states import ThreadSafeDict
from service.scheduler import Scheduler
from service.agent_args import parse_args
from service.agent import LOG_PREFIX, HomeAgent
from service.log import LOGGER
from config import APP_NAME, Config, load_config

LOG_PREFIX = r"[HomeAgent]"
#########################################
def run_service(config: Config, _sensors=None):
    """Run Home Agent Service"""
    LOGGER.info("%s is starting", LOG_PREFIX)

    _state = ThreadSafeDict()
    _running = threading.Event()
    _running.set()

    sched = Scheduler(_state, _running)
    agent = HomeAgent(config, _running, sched, _sensors)

    sched.run(agent.start)
    sched.queue(agent.collector, 10)

    sched.start()

    LOGGER.info("%s Stopping", LOG_PREFIX)
    #agent.stop()

    if _running:
        _running.clear()

    LOGGER.info("%s has stopped", LOG_PREFIX)


#########################################
def main():
    """Main run function"""
    LOGGER.info("Starting %s", APP_NAME)
    _args = parse_args(sys.argv[1:], APP_NAME)

    if _args.get(DEBUG):
        level = logging.getLevelName("DEBUG")
        LOGGER.setLevel(level)
        LOGGER.debug("Debug enabled")

    if _args.get("service") is False:
        LOGGER.error("Must use -s argument to run as a service")
        sys.exit(2)

    try:
        LOGGER.info("%s Loading config file: %s", LOG_PREFIX, _args.get("config"))
        _config = Config(load_config(_args))

        run_service(_config)

    except Exception as err:  # pylint: disable=broad-except
        LOGGER.error(err)
        LOGGER.error(traceback.format_exc())

    LOGGER.info("Quit %s", APP_NAME)


#########################################
if __name__ == "__main__":
    main()
