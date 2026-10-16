from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import Generator
from typing import Iterator

from inline_snapshot._change import ChangeBase
from inline_snapshot._customize._custom import Custom
from inline_snapshot._customize._custom_undefined import CustomUndefined
from inline_snapshot._source_file import SourceFile

if TYPE_CHECKING:
    from .generic_value import GenericValue


class SnapshotOperation:
    """Frame-free behavior and state selected for a snapshot call site."""

    requested: str
    current: str

    def _new_code(self, value: GenericValue) -> Generator[ChangeBase, None, str]:
        raise NotImplementedError

    def _get_changes(self, value: GenericValue) -> Iterator[ChangeBase]:
        raise NotImplementedError


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
    rendered_new_code: str | None = None
    initialized: bool = False
    file: SourceFile | None = None

    def _changes(self) -> Iterator[ChangeBase]:
        return iter(self.changes)

    def __repr__(self) -> str:
        return "snapshot(...)"
