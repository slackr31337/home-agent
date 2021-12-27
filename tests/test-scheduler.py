import unittest
import threading


from utilities.scheduler import Scheduler
from utilities.states import ThreadSafeDict


class TestScheduler(unittest.TestCase):
    def test_scheduler(self):
        self.result = False
        state = ThreadSafeDict()
        running = threading.Event()
        running.set()
        sched = Scheduler(state, running, False)
        sched.run(self.test_func)
        sched.start()
        self.assertEqual(self.result, True)

    def test_func(self):
        self.result = True


if __name__ == "__main__":
    unittest.main()
