from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Generator
from typing import Iterator

if TYPE_CHECKING:
    from inline_snapshot._change import ChangeBase

from .._external_location import ExternalLocation


class StorageLookupError(Exception):
    pass


class StorageProtocol:
    # Does not need to be defined, has a default implementation
    def compare(self, location: ExternalLocation, other_value) -> bool:
        """
        Compare a value against what's stored at the location.

        Default implementation loads the stored value and uses ==.
        Override this for custom comparison logic (e.g., perceptual hashing).

        Returns:
            True if the values match according to this storage's criteria
        """
        # Default implementation for backward compatibility
        with self.load(location) as path:
            stored_value = self._deserialize(path)  # needs to be defined
            return stored_value == other_value

    @contextmanager
    def load(self, location: ExternalLocation) -> Generator[Path]:
        """
        returns the path to a file in the storage.
        """
        raise NotImplementedError

    def store(self, location: ExternalLocation, file_path: Path):
        """
        stores the file in the storage.

        Parameters:

            location: the location in the storage
            file_path: path to a temporaray file which should be stored in the Storage
        """
        raise NotImplementedError

    def delete(self, location: ExternalLocation):
        raise NotImplementedError

    def new_location(
        self, location: ExternalLocation, file_path: Path
    ) -> ExternalLocation:
        """
        creates or changes the location where the file should be stored.
        """
        raise NotImplementedError

    def sync_used_externals(
        self, used_externals: list[ExternalLocation]
    ) -> Iterator[ChangeBase]:
        raise NotImplementedError
