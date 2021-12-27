"""Home Agent event scheduler"""

from collections import deque
import time
import heapq
import signal
import traceback
import threading


from utilities.log import LOGGER
from utilities.util import calc_elasped
from const import SCHEDULER, RUNNING, TASKS, NEXT, LAST, FUNCTION, SLEEP, ARGS, LOG


LOG_PREFIX = "[Scheduler]"
##########################################
class Scheduler:  # pylint: disable=too-many-instance-attributes
    """Event Scheduler Class"""

    ##########################################
    def __init__(self, _state, _running_event, maint=True):
        LOGGER.debug("%s init", LOG_PREFIX)
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        self._task_event = threading.Event()
        self._task_event.clear()
        self.ready = deque()
        self.sleeping = []
        self._state = _state
        self._running_event = _running_event
        self._running = False

        with self._state as _state:
            _state[SCHEDULER] = {RUNNING: False, TASKS: {}}

        self.log_output = None
        self._output_handler = None
        if maint:
            self.queue(self.sched_maint, 600, True)

    ##########################################
    def update_state(self, key, value=None):
        """Update scheduler state dict"""
        with self._state as _state:
            _state[SCHEDULER][key] = value

    ##########################################
    def update_task_state(self, _id, key, value=None):
        """Update task state dict with key, value"""
        with self._state as _state:
            _state[SCHEDULER][TASKS][_id][key] = value

    ##########################################
    def set_task_state(self, _id, func, args, log, _next=0, _sleep=0):
        """Set initial task state dict with details"""
        with self._state as _state:
            _state[SCHEDULER][TASKS][_id] = {
                FUNCTION: func.__name__,
                LAST: 0,
                NEXT: _next,
                SLEEP: _sleep,
                ARGS: args,
                LOG: log,
                RUNNING: False,
            }

    ##########################################
    def state_running(self, _state=True):
        """Set running state"""
        self._running = _state
        self.update_state(RUNNING, _state)
        if _state:
            self.update_state("start", time.time())

    ##########################################
    def sched_maint(self):
        """Remove old states from dict"""
        with self._state as _state:
            for _task, _data in tuple(_state[SCHEDULER][TASKS].items()):
                if _data[NEXT] == 0 and _data[RUNNING] is False:
                    _state[SCHEDULER][TASKS].pop(_task, None)

    ##########################################
    def run(self, func, args=None, log=False):
        """
        Adds the func to the ready queue immediately
        """
        _id = f"{func.__name__}_{int(time.time()*1000)}"
        LOGGER.debug("%s Adding task %s args: %s", LOG_PREFIX, _id, args)
        self.ready.append((_id, func, args, log))
        self.set_task_state(_id, func, args, log)
        if self._running:
            self._task_event.set()
        return _id

    ##########################################
    def queue(
        self, func, sleep=10, forever=False, args=None, log=False
    ):  # pylint: disable=too-many-arguments
        """
        Adds the func to the sleeping queue
        after calcualting deadline
        """
        _id = f"{func.__name__}_{int(time.time()*1000)}"
        LOGGER.debug("%s Scheduling task %s in %s second(s)", LOG_PREFIX, _id, sleep)
        deadline = time.time() + sleep
        heapq.heappush(self.sleeping, (deadline, _id, func, args, log, sleep, forever))
        self.set_task_state(_id, func, args, log, deadline, sleep)
        if self._running:
            self._task_event.set()
        return _id

    ##########################################
    def stop(self, signum=0, frame=None):  # pylint: disable=unused-argument
        """
        Stop running Event loop
        """
        if signum > 0:
            LOGGER.info("%s Received signal %s", LOG_PREFIX, signum)

        LOGGER.info("%s Stopping", LOG_PREFIX)
        self._running_event.clear()
        if self._running:
            self._running = False
            self._task_event.set()

        LOGGER.info("%s Exit", LOG_PREFIX)

    ##########################################
    def start(self):  # pylint: disable=too-many-branches, too-many-statements
        """
        Run the Event loop
        """
        LOGGER.info("%s Starting scheduler", LOG_PREFIX)
        self.state_running()

        while self.ready or self.sleeping:
            timeout = None
            if self._task_event.is_set():
                self.update_state("last_event", time.time())
                self._task_event.clear()

            if not self._running:
                LOGGER.error("%s running is False. Exit", LOG_PREFIX)
                break

            if not self.ready:

                while self.sleeping:
                    timeout = min(int(self.sleeping[0][0] - time.time()), 10)
                    if self.sleeping[0][0] > time.time():
                        break

                    deadline, _id, func, args, log, sleep, forever = heapq.heappop(
                        self.sleeping
                    )

                    self.ready.append((_id, func, args, log))

                    if forever:
                        deadline = time.time() + sleep
                        self.update_task_state(_id, NEXT, deadline)
                        heapq.heappush(
                            self.sleeping,
                            (deadline, _id, func, args, log, sleep, forever),
                        )

            while self.ready:
                start = time.time()
                _id, func, args, log = self.ready.popleft()
                self.update_task_state(_id, LAST, time.time())
                self.update_task_state(_id, RUNNING, True)
                try:
                    if args is not None:
                        func(args)
                    else:
                        func()

                except Exception as err:  # pylint: disable=broad-except
                    LOGGER.error(
                        "%s Exception running task %sk args: %s",
                        LOG_PREFIX,
                        _id,
                        args,
                    )
                    LOGGER.error(err)
                    _trace = traceback.format_exc()
                    LOGGER.error(_trace)

                runtime = calc_elasped(start, None, True)
                self.update_task_state(_id, RUNNING, False)
                self.update_task_state(_id, "runtime", runtime)

                LOGGER.debug(
                    "%s Finished task %s in %s",
                    LOG_PREFIX,
                    _id,
                    runtime,
                )

            if timeout is not None and timeout > 0:
                self._task_event.wait(timeout)

        self.state_running(False)
        LOGGER.info("%s Finished tasks", LOG_PREFIX)

    ##########################################
