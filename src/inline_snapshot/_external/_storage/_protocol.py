from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from .._external_location import ExternalLocation


class StorageLookupError(Exception):
    pass


class StorageProtocol:

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

    def find_unused_externals(
        self, used_externals: list[ExternalLocation]
    ) -> list[ExternalLocation]:
        raise NotImplementedError

    def check_externals(self, used_externals: list[ExternalLocation]):
        """
        This function is executed with all external locations
        at the end of each test session and can be used
        to verify storage specific constraints
        """
