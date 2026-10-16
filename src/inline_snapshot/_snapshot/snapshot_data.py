from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Iterator
from typing import TypeVar

from inline_snapshot._change import ChangeBase
from inline_snapshot._customize._custom import Custom
from inline_snapshot._customize._custom_undefined import CustomUndefined

from ._operation.base import SnapshotOperation

_Operation = TypeVar("_Operation", bound=SnapshotOperation)


@dataclass(eq=False)
class SnapshotData:
    """Frame-free state shared by evaluations of one snapshot call site.

    Context-bearing SnapshotValue facades are intentionally short-lived. Only
    converted values and already-materialized source changes reach this object.
    """

    _old_value: Custom = field(default_factory=CustomUndefined)
    _new_value: Custom = field(default_factory=CustomUndefined)
    operation: SnapshotOperation | None = None
    changes: list[ChangeBase] = field(default_factory=list)
    rendered_new_code: str | None = None
    initialized: bool = False
    filename: Path | None = None

    def use(self, operation_type: type[_Operation]) -> _Operation:
        __tracebackhide__ = True
        if self.operation is None:
            self.operation = operation_type()
        elif not isinstance(self.operation, operation_type):
            raise TypeError(
                f"This snapshot cannot be use with `{operation_type.requested}`, "
                f"because it was previously used with `{self.operation.current}`"
            )
        return self.operation

    def _changes(self) -> Iterator[ChangeBase]:
        return iter(self.changes)

    def __repr__(self) -> str:
        return "snapshot(...)"
