"""Setup logging LOGGER"""

import sys
import logging


#########################################
def log(name="homeagent", level=logging.getLevelName("INFO")):
    """Setup logger"""

    logging.raiseExceptions = False
    _logger = logging.getLogger(name)
    _logger.propagate = False
    _logger.write = lambda msg: _logger.info(msg) if msg != "\n" else None

    _logger.setLevel(level)

    log_stream = logging.StreamHandler(sys.stdout)
    if level == logging.getLevelName("DEBUG"):
        formatter = logging.Formatter(
            "[%(filename)18s: %(funcName)18s()] %(levelname)5s %(message)s"
        )
        log_stream.setFormatter(formatter)

    _logger.addHandler(log_stream)
    return _logger


LOGGER = log()
