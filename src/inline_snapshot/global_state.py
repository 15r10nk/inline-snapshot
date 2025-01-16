from __future__ import annotations

import contextlib
from dataclasses import dataclass
from dataclasses import field

from ._flags import Flags


@dataclass
class State:
    # snapshot
    _missing_values: int = 0
    _incorrect_values: int = 0

    snapshots: dict = field(default_factory=dict)
    _update_flags: Flags = field(default_factory=Flags)
    _active: bool = True
    _files_with_snapshots: set[str] = field(default_factory=set)

    # external
    storage = None


_current = State()
_current._active = False


def state():
    global _current
    return _current


@contextlib.contextmanager
def snapshot_env():

    global _current
    old = _current
    _current = State()

    try:
        yield
    finally:
        _current = old
