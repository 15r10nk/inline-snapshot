from inline_snapshot._core._exceptions import UsageError
from inline_snapshot._core._unmanaged import declare_unmanaged

from ._external_location import ExternalLocation
from ._external_value import load_external_value
from ._storage._protocol import Storage
from ._storage._value import StorageValue


@declare_unmanaged
class ExternalComparison:
    """Compare against a stored value without collecting snapshot changes."""

    def __init__(self, location: ExternalLocation, storage: Storage) -> None:
        self._location = location
        self._storage = storage

    def __eq__(self, other):
        from ._external_base import ExternalBase

        if isinstance(other, (ExternalComparison, ExternalBase)):
            raise UsageError("you cannot compare external(...) with external(...)")
        value = StorageValue(other, self._location)
        return self._storage.lazy_compare(self._location, value)

    def load_value(self) -> object:
        return load_external_value(self._location)

    def __repr__(self):
        return f'external("{self._location.to_str()}")'
