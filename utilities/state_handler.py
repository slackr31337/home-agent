# pylint: disable=consider-using-with
"""Thread safe dict used to hold state info"""

import threading
from threading import get_ident


##########################################
class ThreadSafeDict:
    """Thread safe dict for sharing data between threads"""

    # storage = {}

    ##########################################
    def __init__(self):
        object.__setattr__(self, "storage", {})
        self._local_thread = threading.local()

    ##########################################
    def __setattr__(self, key, value):
        ident = get_ident()
        if ident in self.storage:
            self.storage[ident][key] = value
        else:
            self.storage[ident] = {key: value}

        # print(f"{ident}[{key}] {value}")

    ##########################################
    def __getattr__(self, k):
        ident = get_ident()
        return self.storage[ident][k]


##########################################
def set_state(_state_obj, _key, _value):
    """Set key and value in thread safe dict"""
    with _state_obj as _state:
        _state[_key] = _value


##########################################
def get_state(_state_obj, _key, _default=None):
    """Get value from key in thread safe dict"""
    _value = _state_obj.get(_key)
    if _value is None:
        return _default
    return _value


##########################################
def get_states(_state_obj):
    """Return state dict"""
    return dict(**_state_obj)


##########################################
def inc_state(_state, _key):
    """Increment state counter"""
    count = int(get_state(_state, _key, 0))
    count += 1
    set_state(_state, _key, count)


##########################################
def append_state(_state, _lst, _item):
    """Append item to list in state dict"""
    _data = get_state(_state, _lst)
    _data.append(_item)
    set_state(_state, _lst, _data)
