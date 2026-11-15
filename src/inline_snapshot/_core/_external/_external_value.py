from pathlib import Path
from typing import Any

from inline_snapshot._core._exceptions import UsageError
from inline_snapshot._core._external._format._protocol import get_format_handler
from inline_snapshot._core._external._format._protocol import (
    get_format_handler_from_suffix,
)
from inline_snapshot._core._global_state import state

from ._external_location import ExternalLocation


def serialize_external_value(value: Any, location: ExternalLocation) -> Path:
    format = get_format_handler(value, location.suffix)
    if not location.suffix:
        location.suffix = format.suffix

    path = state().new_tmp_path(location.suffix)
    format.encode(value, path)
    return path


def load_external_value(location: ExternalLocation) -> object:
    assert location.storage

    if not location.stem:
        raise UsageError(
            f"cannot load external object from a non-existing location {location.to_str()!r}"
        )
    storage = state().all_storages[location.storage]

    with storage.load(location) as file:
        assert location.suffix
        format = get_format_handler_from_suffix(location.suffix)
        return format.decode(file)
