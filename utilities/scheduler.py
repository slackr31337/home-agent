"""Home Agent event scheduler"""

from collections import deque
import time
import heapq
import signal
import threading
import traceback


from utilities.log import LOGGER

LOG_PREFIX = "[Scheduler]"
###############################
class Scheduler:
    """Event Scheduler Class"""

    ###########################
    def __init__(self, states):
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)
        self.states = states
        #self.states["scheduler"] = {STARTED: time.time(), "queue": {}, "running": False}
        self.event = threading.Event()
        self.ready = deque()
        self.sleeping = []
        self.running = False

    ###########################
    def run(self, func):
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

        LOGGER.info(
            "%s Task %s() queued to run in %s seconds", LOG_PREFIX, func.__name__, sleep
        )
        try:
            deadline = float(time.time() + sleep)
            heapq.heappush(self.sleeping, (deadline, sleep, forever, func))
        except Exception as err:
            LOGGER.error("%s queue exception %s",LOG_PREFIX, err)
        #if forever:
        #    self.states["scheduler"]["queue"][func.__name__] = {
        #        "job": func,
        #        "sleep": sleep,
        #        "count": 0,
        #        "last": 0,
        #    }
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
                deadline = None
                if self.sleeping:
                    deadline = float(self.sleeping[0][0])
                    sleep = int(deadline - time.time())
                    timeout = min(sleep, 10) if sleep >= 1 else None

                    while deadline is not None and deadline < time.time():
                        deadline, sleep, forever, func = heapq.heappop(self.sleeping)
                        LOGGER.debug(
                            "%s New task is ready: %s()", LOG_PREFIX, func.__name__
                        )

                        self.ready.append(func)

                        if forever:
                            #self.states["scheduler"]["queue"][func.__name__]["count"] += 1
                            #self.states["scheduler"]["queue"][func.__name__][
                            #    "last"
                            #] = time.time()
                            deadline = time.time() + sleep
                            heapq.heappush(self.sleeping, (deadline, sleep, forever, func))

            while self.ready:
                try:
                    func = self.ready.popleft()
                    LOGGER.debug("%s Running task %s()", LOG_PREFIX, func.__name__)
                    
                    func()

                except Exception as err:
                    LOGGER.error("%s Task exception: %s", LOG_PREFIX, err)
                    LOGGER.error(traceback.format_exc())

            if timeout:
                LOGGER.debug("%s Waiting %s seconds", LOG_PREFIX, timeout)
                self.event.wait(timeout)

    LOGGER.info("%s Exit event loop", LOG_PREFIX)
    ###########################
