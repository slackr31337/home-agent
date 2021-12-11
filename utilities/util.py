"""Functions used in modules"""

import psutil
from datetime import datetime

########################################################
def get_boot():
    """Get system boot date and time"""
    boot_time_timestamp = psutil.boot_time()
    bt = datetime.fromtimestamp(boot_time_timestamp)
    return f"{bt.year}-{bt.month}-{bt.day} {bt.hour}:{bt.minute}"


########################################################
