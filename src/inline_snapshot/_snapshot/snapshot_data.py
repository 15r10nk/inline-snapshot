from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Iterator

from inline_snapshot._change import ChangeBase
from inline_snapshot._customize._custom import Custom
from inline_snapshot._customize._custom_undefined import CustomUndefined
from inline_snapshot._source_file import SourceFile


@dataclass(eq=False)
class SnapshotData:
    """Frame-free state shared by evaluations of one snapshot call site."""

    _old_value: Custom = field(default_factory=CustomUndefined)
    _new_value: Custom = field(default_factory=CustomUndefined)
    operation: str | None = None
    changes: list[ChangeBase] = field(default_factory=list)
    operation_changes: list[ChangeBase] | None = None
    rendered_new_code: str | None = None
    initialized: bool = False
    explicit_dispatch: bool = False
    file: SourceFile | None = None
    children: dict[Custom, SnapshotData] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def _changes(self) -> Iterator[ChangeBase]:
        return iter(self.changes)

    def __repr__(self) -> str:
        return "snapshot(...)"
