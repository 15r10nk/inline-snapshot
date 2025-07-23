from __future__ import annotations

import shutil
import uuid
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
