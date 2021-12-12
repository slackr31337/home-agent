"""Functions used in modules"""

import time
import psutil
from datetime import datetime

#########################################
def get_boot():
    """Get system boot date and time"""
    boot = str(datetime.fromtimestamp(psutil.boot_time())).replace(" ", "T")
    return f"{boot}+00:00"


#########################################
def calc_elasped(start, end=None, postfix=True):
    """Calculate time elasped"""

    if end is None:
        end = time.time()
    elasped = end - start
    if not postfix:
        return elasped

    if elasped < 1:
        return f"{int(elasped*1000)} ms"

    return f"{int(elasped)} seconds"
