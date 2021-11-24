"""Home Agent event scheduler"""

from collections import deque
import time
import heapq
import signal


from log import LOGGER

LOG_PREFIX = "[Scheduler]"
###############################
class Scheduler:
    """Event Scheduler Class"""

    ###########################
    def __init__(self):
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)
        self.ready = deque()
        self.sleeping = []
        self.running = False

    ###########################
    def run(self, func):
        """Adds the func to the ready queue immediately"""
        self.ready.append(func)

    ###########################
    def queue(self, sleep, func, forever=False):
        """
        Adds the func to the sleeping queue
        after calcualting deadline
        """
        deadline = time.time() + sleep
        heapq.heappush(self.sleeping, (deadline, sleep, func, forever))

    ###########################
    def stop(self, signum, frame=None):
        """Stop running Event loop"""
        LOGGER.info("%s Received signal %s. Stopping", LOG_PREFIX, signum)
        self.running = False

    ###########################
    def start(self):
        """Run the Event loop"""
        self.running = True

        while self.ready or self.sleeping:
            if not self.running:
                break

            if not self.ready:
                if self.sleeping:
                    deadline = self.sleeping[0][0]
                    timeout = deadline - time.time()
                    if timeout < 0:
                        timeout = 0
                else:
                    timeout = None

                # Check Sleeping tasks
                now = time.time()
                while self.sleeping:
                    if self.sleeping[0][0] < now:
                        deadline, sleep, func, forever = heapq.heappop(self.sleeping)
                        LOGGER.debug(
                            "%s New task is ready %s()", LOG_PREFIX, func.__name__
                        )
                        self.ready.append(func)

                        if forever:
                            LOGGER.debug(
                                "%s Push task %s() back to heap and sleep %s seconds",
                                LOG_PREFIX,
                                func.__name__,
                                sleep,
                            )
                            deadline = time.time() + sleep
                            heapq.heappush(
                                self.sleeping, (deadline, sleep, func, forever)
                            )
                    else:
                        break

            # Execute the ready tasks
            while self.ready:
                func = self.ready.popleft()
                func()

            time.sleep(0.05)

    ###########################
