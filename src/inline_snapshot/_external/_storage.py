from __future__ import annotations

import hashlib
import shutil
import typing
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Generator
from typing import Iterator

if TYPE_CHECKING:
    from inline_snapshot._change import ChangeBase

from ._external_location import ExternalLocation


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

    def sync_used_externals(
        self, used_externals: list[ExternalLocation]
    ) -> Iterator[ChangeBase]:
        raise NotImplementedError


def file_digest(file: typing.BinaryIO, name: str):
    algo = hashlib.new(name)
    algo.update(file.read())
    return algo


class UuidStorage(StorageProtocol):
    @contextmanager
    def load(self, location: ExternalLocation) -> Generator[Path]:
        snapshot_path = self._lookup_path(location)

        yield snapshot_path

    @property
    def _external_files(self):
        from inline_snapshot._global_state import state

        if not hasattr(state(), "_external_files_cache"):

            state()._external_files_cache = {}

            base_folders = {file.parent for file in state().files_with_snapshots}

            test_dir = state().config.tests_dir
            if test_dir:
                base_folders |= set(test_dir.rglob("__inline_snapshot__"))

            for folder in base_folders:
                for file in folder.rglob("????????-????-????-????-????????????.*"):
                    state()._external_files_cache[file.name] = file
        return state()._external_files_cache

    def _lookup_path(self, location: ExternalLocation):
        if location.filename and location.qualname:
            path = self._get_path(location)
            if path.exists():
                return path

        if location.path in self._external_files:
            return self._external_files[location.path]
        else:
            raise StorageLookupError(location)

    def store(self, location: ExternalLocation, file_path: Path):
        snapshot_path = self._get_path(location)

        snapshot_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy(str(file_path), str(snapshot_path))

    def delete(self, location: ExternalLocation):
        snapshot_path = self._lookup_path(location)
        snapshot_path.unlink()

    def new_location(
        self, location: ExternalLocation, file_path: Path
    ) -> ExternalLocation:

        if not location.stem:
            return location.with_stem(str(uuid.uuid4()))
        return location

    def _get_path(self, location: ExternalLocation) -> Path:

        file_path = location.filename
        qualname = location.qualname
        assert file_path
        assert qualname

        if qualname == "<module>":
            qualname = "__module__"

        assert location.stem

        return (
            file_path.parent
            / "__inline_snapshot__"
            / f"{file_path.stem}"
            / qualname
            / f"{location.stem}{location.suffix}"
        )

    def sync_used_externals(
        self, used_externals: list[ExternalLocation]
    ) -> Iterator[ChangeBase]:

        used_names = [location.path for location in used_externals]

        unused_externals = {
            f.name for f in self._external_files.values() if f.name not in used_names
        }

        from inline_snapshot._change import ExternalRemove
        from inline_snapshot._global_state import state

        if state().update_flags.trim:
            for name in unused_externals:
                yield ExternalRemove("trim", ExternalLocation.from_name("uuid:" + name))


class HashStorage(StorageProtocol):
    def __init__(self, directory):
        self.directory = Path(directory)

    def _ensure_directory(self):
        self.directory.mkdir(exist_ok=True, parents=True)
        gitignore = self.directory / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text(
                "# ignore all snapshots which are not referred in the source\n*-new.*\n",
                "utf-8",
            )

    @contextmanager
    def load(self, location: ExternalLocation) -> Generator[Path]:
        path = self._lookup_path(location.path)
        yield path

    def store(self, location: ExternalLocation, file_path: Path):
        self._ensure_directory()

        with file_path.open("rb") as f:
            hash_name = file_digest(f, "sha256").hexdigest()

        assert location.suffix

        if not (self.directory / (hash_name + location.suffix)).exists():
            shutil.copy(
                str(file_path),
                str(self.directory / (hash_name + location.suffix)),
            )

    def delete(self, location: ExternalLocation):
        path = self._lookup_path(location.path)
        path.unlink()

    def new_location(
        self, location: ExternalLocation, file_path: Path
    ) -> ExternalLocation:
        from inline_snapshot._global_state import state

        with file_path.open("rb") as f:
            hash_name = file_digest(f, "sha256").hexdigest()

        path = hash_name[: state().config.hash_length]
        if len(path) < len(hash_name):
            path += "*"

        return location.with_stem(path)

    def sync_used_externals(
        self, used_externals: list[ExternalLocation]
    ) -> Iterator[ChangeBase]:
        unused_externals = self.list()
        for location in used_externals:
            if location.path:
                used = self.lookup_all(location.path)
                unused_externals -= used

        from inline_snapshot._change import ExternalRemove
        from inline_snapshot._global_state import state

        if state().update_flags.trim:
            for name in unused_externals:
                yield ExternalRemove("trim", ExternalLocation.from_name(name))

    def list(self) -> set[str]:

        if self.directory.exists():
            return {item.name for item in self.directory.iterdir()} - {".gitignore"}
        else:
            return set()

    def _lookup_path(self, name) -> Path:
        if "*" not in name:
            p = Path(name)
            name = p.stem + "*" + p.suffix
        files = list(self.directory.glob(name))

        if len(files) > 1:
            raise StorageLookupError(
                f"hash collision files={sorted(f.name for f in  files)}"
            )

        if not files:
            raise StorageLookupError(f"hash {name!r} is not found in the HashStorage")

        return files[0]

    def lookup_all(self, name: str) -> set[str]:
        return {file.name for file in self.directory.glob(name)}


def default_storages(storage_dir: Path):
    return {"hash": HashStorage(storage_dir / "external"), "uuid": UuidStorage()}
