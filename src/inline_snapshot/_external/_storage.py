from __future__ import annotations

import hashlib
import shutil
import typing
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from ._external_location import ExternalLocation


class HashError(Exception):
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

    def new_location(
        self, location: ExternalLocation, file_path: Path
    ) -> ExternalLocation:
        """
        creates or changes the location where the file should be stored.
        """
        raise NotImplementedError

    def cleanup(self):
        raise NotImplementedError


def file_digest(file: typing.BinaryIO, name: str):
    algo = hashlib.new(name)
    algo.update(file.read())
    return algo


class UuidStorage(StorageProtocol):
    @contextmanager
    def load(self, location: ExternalLocation) -> Generator[Path]:
        snapshot_path = self._get_path(location)

        yield snapshot_path

    def store(self, location: ExternalLocation, file_path: Path):
        snapshot_path = self._get_path(location)

        snapshot_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy(str(file_path), str(snapshot_path))

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

        if location.stem:
            stem = location.stem
        else:
            stem = str(uuid.uuid4())
            location.stem = stem

        return (
            file_path.parent
            / "__inline_snapshot__"
            / f"{file_path.stem}"
            / qualname
            / f"{stem}{location.suffix}"
        )

    def cleanup(self):
        pass

    def remove_unused(self, used):
        pass

    def persist(self, name):
        pass


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

        if not (self.directory / (hash_name + location.suffix)).exists():
            # TODO: remove -new
            shutil.copy(
                str(file_path),
                str(self.directory / (hash_name + "-new" + location.suffix)),
            )

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

    def prune_new_files(self):
        for file in self.directory.glob("*-new.*"):
            file.unlink()

    def remove_unused(self, used_externals: list[ExternalLocation]) -> int:
        unused_externals = self.list()
        for location in used_externals:
            unused_externals -= self.lookup_all(location.path)

        n = 0
        for name in unused_externals:
            self.remove(name)
            n += 1

        return n

    def cleanup(self):
        self.prune_new_files()

    def list(self) -> set[str]:

        if self.directory.exists():
            return {item.name for item in self.directory.iterdir()} - {".gitignore"}
        else:
            return set()

    def persist(self, name):
        try:
            file = self._lookup_path(name)
        except HashError:
            return
        if file.stem.endswith("-new"):
            stem = file.stem[:-4]
            file.rename(file.with_name(stem + file.suffix))

    def _lookup_path(self, name) -> Path:
        if "*" not in name:
            p = Path(name)
            name = p.stem + "*" + p.suffix
        files = list(self.directory.glob(name))

        if len(files) > 1:
            raise HashError(f"hash collision files={sorted(f.name for f in  files)}")

        if not files:
            raise HashError(f"hash {name!r} is not found in the HashStorage")

        return files[0]

    def lookup_all(self, name: str) -> set[str]:
        return {file.name for file in self.directory.glob(name)}

    def remove(self, name):
        self._lookup_path(name).unlink()


def default_storages(storage_dir: Path):
    return {"hash": HashStorage(storage_dir / "external"), "uuid": UuidStorage()}
