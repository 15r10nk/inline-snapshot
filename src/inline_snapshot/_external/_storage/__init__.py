from pathlib import Path

from ._hash import HashStorage
from ._protocol import StorageLookupError
from ._protocol import StorageProtocol
from ._uuid import UuidStorage

__all__ = ("StorageLookupError", "StorageProtocol", "HashStorage")


def default_storages(storage_dir: Path):

    return {"hash": HashStorage(storage_dir / "external"), "uuid": UuidStorage()}
