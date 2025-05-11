from __future__ import annotations

from typing import Any

from inline_snapshot._external._external_location import ExternalLocation
from inline_snapshot._external._format import get_format_handler
from inline_snapshot._global_state import state

from .._snapshot.generic_value import GenericValue
from ._tmp_file import generate_tmp_file


class Outsourced:
    def __init__(self, data: Any, suffix: str | None):
        self.data = data

        format = get_format_handler(data, suffix)
        if suffix is None:
            suffix = format.suffix

        self._location = ExternalLocation("hash", None, suffix)

        tmp_path = generate_tmp_file()

        format.encode(data, tmp_path)

        storage = state().all_storages["hash"]

        self._location = storage.new_location(
            self._location, None, tmp_path
        )  # type:ignore

        storage.store(self._location, None, tmp_path)  # type: ignore

    def __eq__(self, other):
        if isinstance(other, GenericValue):
            return NotImplemented

        if isinstance(other, Outsourced):
            return self.data == other.data

        return NotImplemented

    def __repr__(self) -> str:
        return f'external("{self._location.to_str()}")'

    def _load_value(self) -> Any:
        return self.data


def outsource(data, suffix: str | None = None):
    if suffix and suffix[0] != ".":
        raise ValueError("suffix has to start with a '.' like '.png'")

    if not state().active:
        return data

    return Outsourced(data, suffix)
