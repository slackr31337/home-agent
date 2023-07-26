"""Home Agent event scheduler"""

from collections import deque
import time
import heapq
import signal
import traceback
import threading
from typing import Any


from service.log import LOGGER
from service.states import ThreadSafeDict
from service.util import calc_elapsed
from service.const import (
    SCHEDULER,
    RUNNING,
    TASKS,
    NEXT,
    LAST,
    FUNCTION,
    SLEEP,
    ARGS,
    LOG,
)

LOG_PREFIX = r"[Scheduler]"


##########################################
class Scheduler:  # pylint: disable=too-many-instance-attributes
    """Event Scheduler Class"""

    ##########################################
    def __init__(
        self,
        state: ThreadSafeDict,
        running_event: threading.Event,
        run_maintenance: bool = True,
    ):
        LOGGER.debug("%s init", LOG_PREFIX)
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        self._running = False
        self._task_event = threading.Event()
        self._task_event.clear()
        self.ready = deque()
        self.sleeping = []
        self._state = state
        self._running_event = running_event

        with self._state as _state:
            _state[SCHEDULER] = {RUNNING: False, TASKS: {}}

        self.log_output = None
        self._output_handler = None
        if run_maintenance:
            self.queue(self._sched_maint, 600, True)

    ##########################################
    def update_state(self, key: str, value: Any = None):
        """Update scheduler state dict"""

        with self._state as _state:
            _state[SCHEDULER][key] = value

    ##########################################
    def update_task_state(self, task_id, key: str, value: Any = None):
        """Update task state dict with key, value"""

        with self._state as _state:
            _state[SCHEDULER][TASKS][task_id][key] = value

    ##########################################
    def _get_tasks(self) -> list:
        """Return list of task ids"""

        task_ids = []
        with self._state as _state:
            task_ids = list(_state[SCHEDULER][TASKS].keys())

        return task_ids

    ##########################################
    def set_task_state(
        self,
        task_id: str,
        func,
        args: list,
        log: bool,
        next_run: int = 0,
        sleep: int = 0,
    ):
        """Set initial task state dict with details"""

        with self._state as _state:
            _state[SCHEDULER][TASKS][task_id] = {
                FUNCTION: func.__name__,
                LAST: 0,
                NEXT: next_run,
                SLEEP: sleep,
                ARGS: args,
                LOG: log,
                RUNNING: False,
            }

    ##########################################
    def state_running(self, state: bool = True):
        """Set running state"""

        self._running = state
        self.update_state(RUNNING, state)
        if state:
            self.update_state("start", time.time())

    ##########################################
    def _sched_maint(self):
        """Remove old states from dict"""

        with self._state as _state:
            for _task, _data in tuple(_state[SCHEDULER][TASKS].items()):
                if _data[NEXT] == 0 and _data[RUNNING] is False:
                    _state[SCHEDULER][TASKS].pop(_task, None)

    ##########################################
    def _get_task_id(self, name: str) -> str:
        """Return unique task id"""

        task_ids = self._get_tasks()
        _id = None
        while _id is None and _id not in task_ids:
            _id = f"{name}_{int(time.time()*1000)}"
        return _id

    ##########################################
    def run(self, func, args: list = None, log: bool = False) -> str:
        """
        Adds the func to the ready queue immediately
        """

        _id = self._get_task_id(func.__name__)
        self.queue(func, 1, False, args)
        self.set_task_state(_id, func, args, log)
        if self._running:
            self._task_event.set()

        return _id

    ##########################################
    def queue(  # pylint: disable=too-many-arguments
        self,
        func,
        sleep: int = 10,
        forever: bool = False,
        args: list = None,
        log: bool = False,
    ) -> str:
        """
        Adds the func to the sleeping queue
        after calculating deadline
        """

        _id = self._get_task_id(func.__name__)
        LOGGER.debug("%s Scheduling task %s in %s second(s)", LOG_PREFIX, _id, sleep)
        if not isinstance(sleep, int):
            sleep = 10

        deadline = time.time() + sleep
        heapq.heappush(self.sleeping, (deadline, _id, func, args, log, sleep, forever))
        self.set_task_state(_id, func, args, log, deadline, sleep)
        if self._running:
            self._task_event.set()
        return _id

    ##########################################
    def stop(self, sig_num: int = 0, frame=None):  # pylint: disable=unused-argument
        """
        Stop running Event loop
        """
        if sig_num > 0:
            LOGGER.info("%s Received signal %s", LOG_PREFIX, sig_num)

        LOGGER.info("%s Stopping", LOG_PREFIX)
        self._running_event.clear()
        self._task_event.set()
        if self._running:
            self._running = False

        LOGGER.info("%s Exit", LOG_PREFIX)

    ##########################################
    def start(self):  # pylint: disable=too-many-branches, too-many-statements
        """
        Run the Event loop
        """
        LOGGER.info("%s Starting scheduler", LOG_PREFIX)
        self.state_running()
        timeout = 10
        while self.ready or self.sleeping:
            LOGGER.debug(
                "%s [Loop] tasks sleeping %s. timeout: %s",
                LOG_PREFIX,
                len(self.sleeping),
                timeout,
            )

            if self._task_event.is_set():
                self.update_state("last_event", time.time())
                self._task_event.clear()

            if not self._running:
                LOGGER.error("%s running is False. Exit", LOG_PREFIX)
                break

            if self.sleeping:
                timeout = min(int(self.sleeping[0][0] - time.time()), 10)

            if not self.ready:
                while self.sleeping:
                    deadline = self.sleeping[0][0]
                    timeout = int(deadline - time.time())
                    LOGGER.debug(
                        "%s [Sleeping] tasks sleeping %s. timeout: %s",
                        LOG_PREFIX,
                        len(self.sleeping),
                        timeout,
                    )
                    timeout = min(timeout, 3)
                    if deadline > time.time():
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
                LOGGER.debug(
                    "%s [Ready] tasks ready %s. timeout: %s",
                    LOG_PREFIX,
                    len(self.ready),
                    timeout,
                )
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
                    LOGGER.error(traceback.format_exc())

                runtime = calc_elapsed(start, True)
                self.update_task_state(_id, RUNNING, False)
                self.update_task_state(_id, "runtime", runtime)

                LOGGER.debug(
                    "%s Finished task %s in %s",
                    LOG_PREFIX,
                    _id,
                    runtime,
                )

            if len(self.ready) == 0:
                sleep = 1 if timeout < 1 else timeout
                LOGGER.debug(
                    "%s [Wait] tasks sleeping: %s. wait %s.",
                    LOG_PREFIX,
                    len(self.sleeping),
                    sleep,
                )
                self._task_event.wait(sleep)

        self.state_running(False)
        LOGGER.info("%s Finished tasks", LOG_PREFIX)

    ##########################################
