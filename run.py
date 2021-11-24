#!/usr/bin/env python3
"""Run the HomeAgent as a service"""

import sys
import traceback
import logging


from _version import __version__
from log import LOGGER
from agent_args import parse_args
from agent import HomeAgent
from scheduler import Scheduler
from const import APP_NAME


APP_VER = f"{APP_NAME} {__version__}"
########################################################
def run_service(_args, _sensors=None):
    """Run Home Agent Service"""
    LOGGER.info("[HomeAgent] is starting")

    agent = HomeAgent(_args, _sensors)
    sched = Scheduler()

    sched.run(
        agent.start,
    )

    sched.queue(_args.metrics_interval, agent.metrics, True)
    sched.queue(_args.events_interval, agent.events, True)
    sched.queue(_args.modules_interval, agent.modules, True)

    sched.start()

    agent.stop()

    LOGGER.info("[HomeAgent] has stopped")


#########################################
if __name__ == "__main__":
    LOGGER.info("Starting %s", APP_NAME)

    _args = parse_args(sys.argv[1:])
    if _args.debug:
        level = logging.getLevelName("DEBUG")
        LOGGER.setLevel(level)
        LOGGER.debug("Debug enabled")

    if not _args.service:
        LOGGER.error("Must use -s argument to run as a service")
        sys.exit(2)

    try:
        run_service(_args)

    except Exception as err:  # pylint: disable=broad-except
        LOGGER.error(err)
        MSG = traceback.format_exc()
        LOGGER.error(MSG)

    LOGGER.info("Finished %s", APP_NAME)
