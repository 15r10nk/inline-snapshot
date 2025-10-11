from __future__ import annotations

import hashlib
import shutil
import typing
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Generator
from typing import Iterator

if TYPE_CHECKING:
    from inline_snapshot._change import ChangeBase

from .._external_location import ExternalLocation
from ._protocol import StorageLookupError
from ._protocol import StorageProtocol


def file_digest(file: typing.BinaryIO, name: str):
    algo = hashlib.new(name)
    algo.update(file.read())
    return algo


class HashStorage(StorageProtocol):
    def __init__(self, directory):
        self.directory = Path(directory)

    def _ensure_directory(self):
        self.directory.mkdir(exist_ok=True, parents=True)
        gitignore = self.directory / ".gitignore"
        if not gitignore.exists():
            gitignore.write_bytes(
                b"# ignore all snapshots which are not referred in the source\n*-new.*\n"
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
