from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Generator
from typing import Iterator

from inline_snapshot._change import ChangeBase

if TYPE_CHECKING:
    from ..snapshot_value import SnapshotValue


class SnapshotOperation:
    """Frame-free behavior and state selected for a snapshot call site."""

    requested: str
    current: str

    def _new_code(self, value: SnapshotValue) -> Generator[ChangeBase, None, str]:
        raise NotImplementedError

    def _get_changes(self, value: SnapshotValue) -> Iterator[ChangeBase]:
        raise NotImplementedError
