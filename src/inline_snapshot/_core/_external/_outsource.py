from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from inline_snapshot._core._external._format._protocol import get_format_handler
from inline_snapshot._core._global_state import state


@dataclass
class Outsourced:
    data: Any
    suffix: str | None
    storage: str | None

    def __eq__(self, other):
        from inline_snapshot._core._is_snapshot import is_snapshot

        if is_snapshot(other):
            return NotImplemented

        if isinstance(other, Outsourced):
            return self.data == other.data

        return self.data == other


def outsource(data: Any, suffix: str | None = None, storage: str | None = None) -> Any:
    if suffix and suffix[0] != ".":
        raise ValueError("suffix has to start with a '.' like '.png'")

    if not state().active:
        return data

    # check if the suffix/datatype is supported
    get_format_handler(data, suffix or "")

    return Outsourced(data, suffix, storage)
