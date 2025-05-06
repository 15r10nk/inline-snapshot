from __future__ import annotations

import hashlib
import shutil
import typing
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from uuid import uuid4

from .. import _config
from ._external_location import ExternalLocation


class HashError(Exception):
    pass


class StorageProtocol:

    @contextmanager
    def load(self, location: ExternalLocation) -> Generator[typing.BinaryIO]:
        raise NotImplementedError

    @contextmanager
    def store(self, location: ExternalLocation) -> Generator[typing.BinaryIO]:
        raise NotImplementedError


def file_digest(file: typing.BinaryIO, name: str):
    algo = hashlib.new(name)
    algo.update(file.read())
    return algo


class UuidStorage:

    @contextmanager
    def load(self, location: ExternalLocation) -> Generator[typing.BinaryIO]:
        raise NotImplementedError

    @contextmanager
    def store(self, location: ExternalLocation) -> Generator[typing.BinaryIO]:
        raise NotImplementedError


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
    def load(self, location: ExternalLocation) -> Generator[typing.BinaryIO]:
        path = self._lookup_path(location.path)
        with path.open("rb") as f:
            yield f

    @contextmanager
    def store(self, location: ExternalLocation) -> Generator[typing.BinaryIO]:
        self._ensure_directory()

        tmp_name = self.directory / str(uuid4())

        with tmp_name.open("wb") as f:
            yield f

        with tmp_name.open("rb") as f:
            hash_name = file_digest(f, "sha256").hexdigest()

        location.storage = "hash"

        location.stem = hash_name

        assert location.suffix is not None
        if (self.directory / (hash_name + location.suffix)).exists():
            tmp_name.unlink()
        else:
            shutil.move(
                tmp_name, self.directory / (hash_name + "-new" + location.suffix)
            )

        path = hash_name[: _config.config.hash_length]

        if _config.config.hash_length < len(hash_name):
            path += "*"

        location.stem = path

    def prune_new_files(self):
        for file in self.directory.glob("*-new.*"):
            file.unlink()

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

    def lookup_all(self, name) -> set[str]:
        return {file.name for file in self.directory.glob(name)}

    def remove(self, name):
        self._lookup_path(name).unlink()
