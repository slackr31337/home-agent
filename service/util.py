"""Functions used in modules"""

import time
from datetime import datetime
import psutil


#########################################
def get_boot() -> str:
    """Get system boot date and time"""

    boot = str(datetime.fromtimestamp(psutil.boot_time())).replace(" ", "T")
    return f"{boot}+00:00"


#########################################
def calc_elapsed(start: float, postfix: bool = True) -> str:
    """Calculate time elapsed"""

    end = time.time()
    elapsed = end - start
    if not postfix:
        return elapsed

    if elapsed < 1:
        elapsed = int(elapsed * 1000)
        postfix = "ms"

    elif elapsed > 1:
        postfix = "seconds"
    else:
        postfix = "second"

    return f"{int(elapsed)} {postfix}"


##########################################
def gps_moving(data: dict) -> bool:
    """Check if speed is > 0"""
    if not isinstance(data, dict):
        speed = 0
    else:
        speed = int(data.get("speed", 0))

    if speed and speed > 2:
        return True
    return False


##########################################
def gps_update(last: int = 0) -> bool:
    """Check if speed is > 0"""
    if not isinstance(last, int):
        last = 0
    now = int(time.time())
    delta = int(now - last)
    if last is None or delta > 3600:
        return True
    return False
