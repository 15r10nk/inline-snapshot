from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Generator

from inline_snapshot._core._exceptions import ValueNotFound

from .._external_location import ExternalLocation

if TYPE_CHECKING:
    from ._value import StorageValue


class StorageLookupError(ValueNotFound):
    def __init__(self, msg, files):
        super().__init__(msg)
        self.files = files


class Storage:
    def lazy_compare(self, location: ExternalLocation, other: StorageValue) -> bool:
        """Optionally compare a stored snapshot with a lazy comparison value.

        ``other.value`` is the original Python value. ``other.data`` lazily
        serializes it and returns a cached temporary file path.

        Backends overriding this method use it in both active and disabled
        snapshot modes. Other backends use the decoded value and ==.
        """
        raise NotImplementedError

    @contextmanager
    def load(self, location: ExternalLocation) -> Generator[Path]:
        """
        returns the path to a file in the storage.
        """
        raise NotImplementedError

    def store(self, location: ExternalLocation, file_path: Path):
        """Persist the serialized contents at a prepared location.

        Called only when the corresponding snapshot change is accepted. Copy or
        upload the complete contents before returning: ``file_path`` is a
        temporary file owned by inline-snapshot and may be removed afterwards.
        Do not modify or delete the source file.

        Subsequent ``load(location)`` calls must expose the supplied contents.
        Mutable backends overwrite existing contents at that location;
        content-addressed backends choose a new location in ``new_location``
        when the contents change and may reuse identical existing data.
        """
        raise NotImplementedError

    def delete(self, location: ExternalLocation):
        raise NotImplementedError

    def new_location(
        self, location: ExternalLocation, file_path: Path
    ) -> ExternalLocation:
        """Prepare the location for serialized contents without persisting them.

        This runs during comparison, including report mode, before the user
        accepts any changes. Do not create, overwrite, or delete persistent
        snapshots, or reserve persistent resources here. Persist data only in
        ``store`` after the change is accepted.

        Return the existing location or one with a new stem, preserving the
        storage name, format suffix, and source metadata. Do not modify or
        delete ``file_path``; it is owned by inline-snapshot.
        """
        raise NotImplementedError

    def find_unused_externals(
        self, used_externals: list[ExternalLocation]
    ) -> list[ExternalLocation]:
        """List unused snapshots when trimming is requested and allowed.

        Return candidates without deleting them. Deletion is applied separately
        after the corresponding changes are accepted.
        """
        raise NotImplementedError

    def check_externals(self, used_externals: list[ExternalLocation]):
        """
        This function is executed with all external locations
        at the end of each test session and can be used
        to verify storage specific constraints
        """
