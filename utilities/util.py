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
def calc_elasped(start: float, postfix: bool = True) -> str:
    """Calculate time elasped"""

    end = time.time()
    elasped = end - start
    if not postfix:
        return elasped

    if elasped < 1:
        elasped = int(elasped * 1000)
        postfix = "ms"

    elif elasped > 1:
        postfix = "seconds"
    else:
        postfix = "second"

    return f"{int(elasped)} {postfix}"
