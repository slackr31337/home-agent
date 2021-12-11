#!/usr/bin/env python3
"""Run the HomeAgent as a service"""

import sys
import traceback
import logging


from utilities.log import LOGGER
from utilities.scheduler import Scheduler
from config import APP_NAME, Config, load_config
from agent_args import parse_args
from agent import LOG_PREFIX, HomeAgent


LOG_PREFIX = "[HomeAgent]"
########################################################
def run_service(_config, _sensors=None):
    """Run Home Agent Service"""
    LOGGER.info("%s is starting", LOG_PREFIX)

    agent = HomeAgent(_config, _sensors)
    sched = Scheduler()

    sched.run(
        agent.start,
    )

    sched.queue(agent.metrics, _config.intervals.metrics, True)
    sched.queue(agent.events, _config.intervals.events, True)
    sched.queue(agent.modules, _config.intervals.modules, True)
    sched.queue(agent.conn_ping, _config.intervals.ping, True)

    sched.start()

    agent.stop()

    LOGGER.info("%s has stopped", LOG_PREFIX)


#########################################
if __name__ == "__main__":
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

    LOGGER.info("Finished %s", APP_NAME)
