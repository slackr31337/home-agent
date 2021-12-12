"""Home Agent event scheduler"""

from collections import deque
import time
import heapq
import signal
import threading


from utilities.log import LOGGER
from const import STARTED

LOG_PREFIX = "[Scheduler]"
###############################
class Scheduler:
    """Event Scheduler Class"""

    ###########################
    def __init__(self, states):
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)
        self.states = states
        self.states["scheduler"] = {STARTED: time.time(), "queue": {}, "running": False}
        self.event = threading.Event()
        self.ready = deque()
        self.sleeping = []
        self.running = False

    ###########################
    def run(self, func, **args):
        """Adds the func to the ready queue immediately"""
        LOGGER.info("%s Task %s() scheduled to run", LOG_PREFIX, func.__name__)
        self.ready.append(func)
        if self.running:
            self.event.set()

    ###########################
    def queue(self, func, sleep=10, forever=False):
        """
        Adds the func to the sleeping queue
        after calcualting deadline
        """
        deadline = time.time() + sleep
        heapq.heappush(self.sleeping, (deadline, sleep, forever, func))
        LOGGER.info(
            "%s Task %s() queued to run in %s seconds", LOG_PREFIX, func.__name__, sleep
        )
        if forever:
            self.states["scheduler"]["queue"][func.__name__] = {
                "job": func,
                "sleep": sleep,
                "count": 0,
                "last": 0,
            }
        if self.running:
            self.event.set()

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
                    sleep = int(deadline - time.time())
                    timeout = min(sleep, 10) if sleep >= 1 else None
                else:
                    deadline = None

                while deadline and deadline < time.time():
                    # if self.sleeping[0][0] < time.time():
                    deadline, sleep, forever, func = heapq.heappop(self.sleeping)
                    LOGGER.debug(
                        "%s New task is ready: %s()", LOG_PREFIX, func.__name__
                    )

                    self.ready.append(func)

                    if forever:
                        self.states["scheduler"]["queue"][func.__name__]["count"] += 1
                        self.states["scheduler"]["queue"][func.__name__][
                            "last"
                        ] = time.time()
                        deadline = time.time() + sleep
                        heapq.heappush(self.sleeping, (deadline, sleep, forever, func))

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
