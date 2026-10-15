from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Iterator

from inline_snapshot._change import ChangeBase
from inline_snapshot._customize._custom import Custom
from inline_snapshot._customize._custom_undefined import CustomUndefined
from inline_snapshot._source_file import SourceFile


class SnapshotOperation(Enum):
    EQ = ("==", "x == snapshot")
    MIN = ("<=", "x >= snapshot")
    MAX = (">=", "x <= snapshot")
    COLLECTION = ("in", "x in snapshot")
    DICT = ("snapshot[key]", "snapshot[key]")

    def __init__(self, requested: str, current: str):
        self.requested = requested
        self.current = current


@dataclass(eq=False)
class SnapshotData:
    """Frame-free state shared by evaluations of one snapshot call site.

    Context-bearing GenericValue facades are intentionally short-lived. Only
    converted values and already-materialized source changes reach this object.
    """

    _old_value: Custom = field(default_factory=CustomUndefined)
    _new_value: Custom = field(default_factory=CustomUndefined)
    operation: SnapshotOperation | None = None
    changes: list[ChangeBase] = field(default_factory=list)
    operation_changes: list[ChangeBase] | None = None
    element_changes: list[ChangeBase] = field(default_factory=list)
    rendered_new_code: str | None = None
    initialized: bool = False
    file: SourceFile | None = None
    children: dict[Custom, SnapshotData] = field(default_factory=dict)

    def _changes(self) -> Iterator[ChangeBase]:
        return iter(self.changes)

    def __repr__(self) -> str:
        return "snapshot(...)"
