from functools import cached_property
from pathlib import Path
from typing import Any

from .._external_location import ExternalLocation
from .._external_value import serialize_external_value


class StorageValue:
    """A comparison value with lazily serialized file data.

    ``value`` is the original Python value. ``data`` serializes it on first
    access and returns the same temporary file path on subsequent accesses.
    The file is managed by inline-snapshot and remains valid for the session.
    Backends must not modify or delete it.
    """

    def __init__(self, value: Any, location: ExternalLocation) -> None:
        self.value = value
        self._location = location

    @cached_property
    def data(self) -> Path:
        """The temporary file containing the serialized value."""
        return serialize_external_value(self.value, self._location)
