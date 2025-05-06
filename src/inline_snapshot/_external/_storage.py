from __future__ import annotations

import hashlib
import shutil
import typing
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from inline_snapshot._adapter.adapter import AdapterContext

from .. import _config
from ._external_location import ExternalLocation


class HashError(Exception):
    pass


class StorageProtocol:

    @contextmanager
    def load(
        self, location: ExternalLocation, context: AdapterContext
    ) -> Generator[typing.BinaryIO]:
        raise NotImplementedError

    @contextmanager
    def store(
        self, location: ExternalLocation, context: AdapterContext
    ) -> Generator[typing.BinaryIO]:
        raise NotImplementedError

    def cleanup(self):
        raise NotImplementedError


def file_digest(file: typing.BinaryIO, name: str):
    algo = hashlib.new(name)
    algo.update(file.read())
    return algo


class UuidStorage(StorageProtocol):
    @contextmanager
    def load(
        self, location: ExternalLocation, context: AdapterContext
    ) -> Generator[typing.BinaryIO]:
        snapshot_path = self._get_path(location, context)

        with snapshot_path.open("rb") as f:
            yield f

    @contextmanager
    def store(
        self, location: ExternalLocation, context: AdapterContext
    ) -> Generator[typing.BinaryIO]:
        snapshot_path = self._get_path(location, context)

        snapshot_path.parent.mkdir(parents=True, exist_ok=True)

        with snapshot_path.open("wb") as f:
            yield f

    def _get_path(self, location: ExternalLocation, context: AdapterContext) -> Path:

        file_path = Path(context.file.filename)
        qualname = context.qualname
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
    def load(
        self, location: ExternalLocation, context: AdapterContext
    ) -> Generator[typing.BinaryIO]:
        path = self._lookup_path(location.path)
        with path.open("rb") as f:
            yield f

    @contextmanager
    def store(
        self, location: ExternalLocation, context: AdapterContext
    ) -> Generator[typing.BinaryIO]:
        self._ensure_directory()

        tmp_name = self.directory / str(uuid.uuid4())

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
