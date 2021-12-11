"""Home Agent event scheduler"""

from collections import deque
import time
import heapq
import signal
import threading


from utilities.log import LOGGER

LOG_PREFIX = "[Scheduler]"
###############################
class Scheduler:
    """Event Scheduler Class"""

    ###########################
    def __init__(self):
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)
        self.event = threading.Event()
        self.event.clear()
        self.ready = deque()
        self.sleeping = []
        self.running = False

    ###########################
    def run(self, func):
        """Adds the func to the ready queue immediately"""
        LOGGER.info("%s Task %s() scheduled to run", LOG_PREFIX, func.__name__)
        self.ready.append(func)
        self.event.set()

    ###########################
    def queue(self, func, sleep=10, forever=False):
        """
        Adds the func to the sleeping queue
        after calcualting deadline
        """
        deadline = time.time() + sleep
        heapq.heappush(self.sleeping, (deadline, func, sleep, forever))
        self.event.set()
        LOGGER.info(
            "%s Task %s() queued to run in %s seconds", LOG_PREFIX, func.__name__, sleep
        )

    ###########################
    def stop(self, signum=0, frame=None):
        """Stop running Event loop"""
        if signum > 0:
            LOGGER.info("%s Received signal %s. Stopping", LOG_PREFIX, signum)
        self.event.set()
        self.running = False

    ###########################
    def start(self):
        """Run the Event loop"""
        self.event.clear()
        self.running = True
        timeout = None

        while self.ready or self.sleeping:
            if not self.running:
                break

            if self.event.is_set():
                self.event.clear()

            if not self.ready:
                if self.sleeping:
                    deadline = self.sleeping[0][0]
                    timeout = int(deadline - time.time())
                    if timeout < 1:
                        timeout = None
                    elif timeout > 10:
                        timeout = 10
                else:
                    timeout = None

                while self.sleeping:
                    if self.sleeping[0][0] < time.time():
                        deadline, func, sleep, forever = heapq.heappop(self.sleeping)
                        LOGGER.debug(
                            "%s New task is ready: %s()", LOG_PREFIX, func.__name__
                        )
                        self.ready.append(func)

                        if forever:
                            deadline = time.time() + sleep
                            heapq.heappush(
                                self.sleeping, (deadline, func, sleep, forever)
                            )
                    else:
                        break

            while self.ready:
                func = self.ready.popleft()
                LOGGER.debug("%s Running task %s()", LOG_PREFIX, func.__name__)
                try:
                    func()
                except Exception as err:
                    LOGGER.error("%s Task exception: %s", LOG_PREFIX, err)

            if timeout:
                LOGGER.debug("%s Waiting %s seconds", LOG_PREFIX, timeout)
                self.event.wait(timeout)

    LOGGER.info("%s Exit event loop", LOG_PREFIX)
    ###########################
