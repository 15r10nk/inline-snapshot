from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Iterator

from inline_snapshot._change import ChangeBase
from inline_snapshot._change import ExternalChange
from inline_snapshot._exceptions import UsageError
from inline_snapshot._external._format._protocol import get_format_handler
from inline_snapshot._external._outsource import Outsourced
from inline_snapshot._external._storage._protocol import StorageLookupError
from inline_snapshot._global_state import state

from .._snapshot.snapshot_value import SnapshotValue
from ._external_location import ExternalLocation
from ._external_location import Location


@dataclass(eq=False, kw_only=True)
class ExternalBaseData:
    original_location: Location
    location: Location
    tmp_file: Path | None = None
    was_compared: bool = False
    changes: list[ChangeBase] = field(default_factory=list)

    def _changes(self) -> Iterator[ChangeBase]:
        return iter(self.changes)


class ExternalBase:
    _data: ExternalBaseData

    @property
    def _original_location(self):
        return self._data.original_location

    @_original_location.setter
    def _original_location(self, value):
        self._data.original_location = value

    @property
    def _location(self):
        return self._data.location

    @_location.setter
    def _location(self, value):
        self._data.location = value

    @property
    def _tmp_file(self):
        return self._data.tmp_file

    @_tmp_file.setter
    def _tmp_file(self, value):
        self._data.tmp_file = value

    @property
    def _was_compared(self):
        return self._data.was_compared

    @_was_compared.setter
    def _was_compared(self, value):
        self._data.was_compared = value

    def _changes(self):
        if self._tmp_file is not None:
            yield ExternalChange(
                "create" if self._is_empty() else "fix",
                self._tmp_file,
                self._original_location,
                self._location,
                self._format,
            )

    def _assign(self, value):
        raise NotImplementedError()

    def _load_value(self, which):
        raise NotImplementedError()

    def __eq__(self, other):
        """Two external objects are equal if they have the same value"""

        __tracebackhide__ = True
        result = self._compare(other)
        self._data.changes = list(self._changes())
        return result

    def _compare(self, other):
        __tracebackhide__ = True

        external_type = (
            "external" if type(self).__name__ == "External" else "external_file"
        )
        if isinstance(other, Outsourced):

            format = get_format_handler(other.data, other.suffix or "")

            self._location.suffix = other.suffix or format.suffix
            other = other.data

        elif isinstance(other, ExternalBase):
            raise UsageError(
                f"you cannot compare {external_type}(...) with {external_type}(...)"
            )

        elif isinstance(other, SnapshotValue):
            raise UsageError(
                f"you cannot compare {external_type}(...) with snapshot(...)"
            )

        first_comparison = not self._was_compared

        self._was_compared = True

        if self._is_empty():
            self._assign(other)
            state().missing_values += 1
            if state().update_flags.create:
                return True
            return False

        try:
            value = self._load_value("old")
        except StorageLookupError as error:
            if not error.files and state().update_flags.fix:
                self._original_location = ExternalLocation.from_name("")
                self._assign(other)
                state().incorrect_values += 1
                return True
            else:
                raise

        result = value == other

        if not result and first_comparison:
            self._assign(other)
            state().incorrect_values += 1
            return True
        return result
