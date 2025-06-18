from __future__ import annotations

import contextlib
from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from typing import Any
from typing import Generator

from inline_snapshot._config import Config
from inline_snapshot._external._format._protocol import Format
from inline_snapshot._external._storage._protocol import StorageProtocol
from inline_snapshot._types import SnapshotRefBase

from ._flags import Flags

if TYPE_CHECKING:
    pass


@dataclass
class State:
    config: Config = field(default_factory=Config)

    # snapshot
    missing_values: int = 0
    incorrect_values: int = 0

    snapshots: dict[Any, SnapshotRefBase] = field(default_factory=dict)
    update_flags: Flags = field(default_factory=Flags)
    active: bool = True

    @property
    def files_with_snapshots(self):
        return {
            Path(s._context.file.filename)
            for s in self.snapshots.values()
            if hasattr(s, "_context")
        }

    flags: set[str] = field(default_factory=set)

    format_aliases: dict[str, str] = field(default_factory=dict)

    all_formats: dict[str, Format] = field(default_factory=dict)

    all_storages: dict[str, StorageProtocol] = field(default_factory=dict)

    default_storage: str = "hash"


_latest_global_states: list[State] = []

_current: State = State()
_current.active = False


def state() -> State:
    global _current
    return _current


def enter_snapshot_context():
    global _current
    latest = _current
    _latest_global_states.append(_current)
    _current = State()
    _current.all_formats = dict(latest.all_formats)
    _current.config = deepcopy(latest.config)


def leave_snapshot_context():
    global _current
    _current = _latest_global_states.pop()


@contextlib.contextmanager
def snapshot_env() -> Generator[State]:
    from ._external._storage._hash import HashStorage

    old = _current

    enter_snapshot_context()

    try:
        with TemporaryDirectory() as dir:
            _current.all_storages = dict(old.all_storages)
            _current.all_storages["hash"] = HashStorage(dir)

            yield _current
    finally:
        leave_snapshot_context()
