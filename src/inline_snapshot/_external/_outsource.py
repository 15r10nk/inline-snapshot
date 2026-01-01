from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from inline_snapshot._customize import Builder
from inline_snapshot._customize import customize
from inline_snapshot._external._format._protocol import get_format_handler
from inline_snapshot._global_state import state
from inline_snapshot._snapshot.generic_value import GenericValue


@dataclass
class Outsourced:
    data: Any
    suffix: str | None
    storage: str | None

    def __eq__(self, other):
        if isinstance(other, GenericValue):
            return NotImplemented

        if isinstance(other, Outsourced):
            return self.data == other.data

        from inline_snapshot._external._external_base import ExternalBase

        if isinstance(other, ExternalBase):
            return NotImplemented

        return self.data == other


@customize
def outsource_handler(value, builder: Builder):
    if isinstance(value, Outsourced):
        return builder.create_external(
            value.data, format=value.suffix, storage=value.storage
        )


def outsource(data: Any, suffix: str | None = None, storage: str | None = None) -> Any:
    if suffix and suffix[0] != ".":
        raise ValueError("suffix has to start with a '.' like '.png'")

    if not state().active:
        return data

    # check if the suffix/datatype is supported
    get_format_handler(data, suffix or "")

    return Outsourced(data, suffix, storage)
