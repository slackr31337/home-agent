import sys
import logging


#########################################
def log(name="homeagent"):
    """Setup logger"""
    _LOGGER = logging.getLogger(name)

    level = logging.getLevelName("INFO")
    _LOGGER.setLevel(level)

    log_stream = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(levelname)8s %(funcName)22s() %(message)s")
    log_stream.setFormatter(formatter)
    _LOGGER.addHandler(log_stream)
    return _LOGGER


LOGGER = log()
