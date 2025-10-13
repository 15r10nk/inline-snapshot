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
from typing import Literal
from uuid import uuid4

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

    all_problems: set[str] = field(default_factory=set)

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

    default_storage: str = "uuid"

    tmp_dir: TemporaryDirectory | None = field(
        default_factory=lambda: TemporaryDirectory(prefix="inline-snapshot-")
    )

    def new_tmp_path(self, suffix: str) -> Path:
        assert self.tmp_dir is not None
        return Path(self.tmp_dir.name) / f"tmp-path-{uuid4()}{suffix}"

    disable_reason: Literal["xdist", "ci", "implementation", None] = None


_latest_global_states: list[State] = []

_current: State = State(active=False, tmp_dir=None)


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
    _current.tmp_dir.cleanup()
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
