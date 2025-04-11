from __future__ import annotations

import contextlib
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import Generator

from ._flags import Flags

if TYPE_CHECKING:
    from ._external import DiscStorage


@dataclass
class State:
    # snapshot
    missing_values: int = 0
    incorrect_values: int = 0

    snapshots: dict = field(default_factory=dict)
    update_flags: Flags = field(default_factory=Flags)
    active: bool = True
    files_with_snapshots: set[str] = field(default_factory=set)

    # external
    storage: DiscStorage | None = None

    flags: set[str] = field(default_factory=set)


_latest_global_states: list[State] = []

_current: State = State()
_current.active = False


def state() -> State:
    global _current
    return _current


def enter_snapshot_context():
    global _current
    _latest_global_states.append(_current)
    _current = State()


def leave_snapshot_context():
    global _current
    _current = _latest_global_states.pop()


@contextlib.contextmanager
def snapshot_env() -> Generator[State]:

    enter_snapshot_context()

    try:
        yield _current
    finally:
        leave_snapshot_context()
