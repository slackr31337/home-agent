#!/usr/bin/env python3
"""Run the HomeAgent as a service"""

import sys
import threading
import traceback
import logging


from utilities.log import LOGGER
from utilities.scheduler import Scheduler
from utilities.states import ThreadSafeDict
from agent_args import parse_args
from agent import LOG_PREFIX, HomeAgent
from config import APP_NAME, Config, load_config

LOG_PREFIX = "[HomeAgent]"
#########################################
def run_service(_config, _sensors=None):
    """Run Home Agent Service"""
    LOGGER.info("%s is starting", LOG_PREFIX)

    state = ThreadSafeDict()
    running = threading.Event()
    running.set()

    sched = Scheduler(state, running)
    agent = HomeAgent(_config, running, sched, _sensors)

    sched.run(agent.start)
    sched.queue(agent.metrics, 10)
    sched.queue(agent.events, 10)

    sched.queue(agent.metrics, _config.intervals.metrics, True)
    sched.queue(agent.events, _config.intervals.events, True)
    sched.queue(agent.modules, _config.intervals.modules, True)
    sched.queue(agent.conn_ping, _config.intervals.ping, True)

    sched.start()

    LOGGER.info("%s Stopping", LOG_PREFIX)
    agent.stop()
    running.clear()

    LOGGER.info("%s has stopped", LOG_PREFIX)


#########################################
def main():
    """Main run function"""
    LOGGER.info("Starting %s", APP_NAME)
    _args = parse_args(sys.argv[1:], APP_NAME)

    if _args.debug:
        level = logging.getLevelName("DEBUG")
        LOGGER.setLevel(level)
        LOGGER.debug("Debug enabled")

    if not _args.service:
        LOGGER.error("Must use -s argument to run as a service")
        sys.exit(2)

    LOGGER.info("%s Loading config file: %s", LOG_PREFIX, _args.config)
    _config = Config(load_config(_args.config))

    try:
        run_service(_config)

    except Exception as err:  # pylint: disable=broad-except
        LOGGER.error(err)
        LOGGER.error(traceback.format_exc())

    LOGGER.info("Quit %s", APP_NAME)


#########################################
if __name__ == "__main__":
    main()
