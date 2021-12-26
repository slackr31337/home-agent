import sys
import logging


#########################################
def log(name="homeagent"):
    """Setup logger"""
    logging.raiseExceptions = False
    _LOGGER = logging.getLogger(name)

    level = logging.getLevelName("INFO")
    _LOGGER.setLevel(level)

    log_stream = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[%(filename)18s: %(funcName)18s()] %(levelname)5s %(message)s"
    )
    log_stream.setFormatter(formatter)
    _LOGGER.addHandler(log_stream)
    return _LOGGER


LOGGER = log()
