from __future__ import annotations

from pathlib import Path

from inline_snapshot._change import ExternalChange
from inline_snapshot._exceptions import UsageError
from inline_snapshot._external._outsource import Outsourced
from inline_snapshot._global_state import state

from .._snapshot.generic_value import GenericValue
from ._external_location import Location


class ExternalBase:

    _original_location: Location
    _location: Location
    _tmp_file: Path | None

    def __init__(self):
        self._tmp_file = None
        self._was_compared = False

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

    def _load_value(self):
        raise NotImplementedError()

    def __eq__(self, other):
        """Two external objects are equal if they have the same value"""

        external_type = (
            "external" if type(self).__name__ == "External" else "external_file"
        )
        __tracebackhide__ = True

        if isinstance(other, Outsourced):
            self._location.suffix = other._location.suffix
            other = other.data

        if isinstance(other, ExternalBase):
            raise UsageError(
                f"you can not compare {external_type}(...) with {external_type}(...)"
            )

        if isinstance(other, GenericValue):
            raise UsageError(
                f"you can not compare {external_type}(...) with snapshot(...)"
            )

        first_comparison = not self._was_compared

        self._was_compared = True

        if self._is_empty():
            self._assign(other)
            state().missing_values += 1
            if state().update_flags.create:
                return True
            return False

        value = self._load_value()
        result = value == other

        if not result and first_comparison:
            self._assign(other)
            state().incorrect_values += 1
            return True
        return result
