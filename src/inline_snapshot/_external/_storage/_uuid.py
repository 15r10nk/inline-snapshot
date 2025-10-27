from __future__ import annotations

import shutil
import uuid
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from inline_snapshot._global_state import state_cached
from inline_snapshot._problems import raise_problem
from inline_snapshot._utils import link

from .._external_location import ExternalLocation
from ._protocol import StorageLookupError
from ._protocol import StorageProtocol


@state_cached
def external_files() -> dict[str, Path]:
    from inline_snapshot._global_state import state

    base_folders = set()

    for test_dir in state().config.test_directories or []:
        base_folders |= set(test_dir.rglob("__inline_snapshot__"))

    return {
        file.name: file
        for folder in base_folders
        for file in folder.rglob("????????-????-????-????-????????????.*")
    }


class UuidStorage(StorageProtocol):
    @contextmanager
    def load(self, location: ExternalLocation) -> Generator[Path]:
        snapshot_path = self._lookup_path(location)

        yield snapshot_path

    def _lookup_path(self, location: ExternalLocation):
        if location.filename and location.qualname:
            path = self._get_path(location)
            if path.exists():
                return path

        if location.path in external_files():
            return external_files()[location.path]
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

    def find_unused_externals(
        self, used_externals: list[ExternalLocation]
    ) -> list[ExternalLocation]:

        used_names = [location.path for location in used_externals]

        unused_externals = {
            f.name for f in external_files().values() if f.name not in used_names
        }

        return [ExternalLocation.from_name("uuid:" + name) for name in unused_externals]

    def check_externals(self, used_externals: list[ExternalLocation]):
        grouped = defaultdict(list)
        for external in used_externals:
            grouped[external.to_str()].append(external)

        for external, externals in grouped.items():
            if len(externals) > 1:
                raise_problem(
                    f"The external {external} is used multiple times, which is not supported:\n"
                    + "\n".join(
                        sorted(
                            f"   {e.filename.resolve().relative_to(Path.cwd().resolve()).as_posix()}:{e.linenumber}"
                            for e in externals
                            if e.filename
                        )
                    )
                    + f"\n   (see {link('https://15r10nk.github.io/inline-snapshot/latest/external/external/#uuid')})"
                )
