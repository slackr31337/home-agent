# pylint: disable=consider-using-with
"""Thread safe dict used to hold state info"""

import os
import threading
import json


from service.log import LOGGER
from service.const import STATE, ATTRIBS, DEVICE

LOG_PREFIX = r"[State]"
##########################################
class ThreadSafeDict(dict):
    """Thread safe dict for sharing data between threads"""

    def __init__(self, *p_arg, **n_arg):
        dict.__init__(self, *p_arg, **n_arg)
        self._lock = threading.Lock()

    def __enter__(self):
        self._lock.acquire()
        return self

    def __exit__(self, _type, _value, _traceback):
        self._lock.release()


##########################################
def set_state(state_obj: ThreadSafeDict, key: str, value):
    """Set key and value in thread safe dict"""
    with state_obj as _state:
        _state[key] = value


###########################
def get_state(state_obj: ThreadSafeDict, key: str, default=None):
    """Get value from key in thread safe dict"""
    _value = state_obj.get(key)
    if _value is None:
        return default
    return _value


##########################################
def get_states(state_obj: ThreadSafeDict) -> dict:
    """Return state dict"""
    return dict(**state_obj)


##########################################
def inc_state(state: ThreadSafeDict, key: str):
    """Increment state counter"""
    count = int(get_state(state, key, 0))
    count += 1
    set_state(state, key, count)


##########################################
def append_state(state: ThreadSafeDict, lst: list, item):
    """Append item to list in state dict"""
    _data = get_state(state, lst)
    _data.append(item)
    set_state(state, lst, _data)


##########################################
def load_states(state_file: str) -> dict:
    """Read states dict from JSON file"""

    LOGGER.debug("%s Loading states from %s", LOG_PREFIX, state_file)

    if not os.path.exists(state_file):
        LOGGER.error("%s Failed to load states from %s", LOG_PREFIX, state_file)
        return None

    states = None
    with open(state_file, "r", encoding="utf-8") as read_file:
        data = read_file.read()

    try:
        states = json.loads(data)

    except json.JSONDecodeError as err:
        LOGGER.error("%s Failed to load states from json", LOG_PREFIX)
        LOGGER.error(err)

    return states


##########################################
def save_states(states_file: str, states: dict, attribs: dict, device: dict):
    """Save states and attribs dicts to JSON file"""

    with open(states_file, "w", encoding="utf-8") as write_file:
        _state = {
            STATE: states,
            ATTRIBS: attribs,
            DEVICE: device,
        }
        if "screen_capture" in _state[STATE]:
            _state[STATE].pop("screen_capture")
        write_file.write(json.dumps(_state, default=str, indent=4))
