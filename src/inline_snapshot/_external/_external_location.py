from __future__ import annotations

import dataclasses
import re
import shutil
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

from inline_snapshot._adapter.adapter import AdapterContext


class Location:
    suffix: str

    def __str__(self) -> str:
        raise NotImplementedError

    @contextmanager
    def load(self) -> Generator[Path]:
        raise NotImplementedError

    def store(self, new_file: Path):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError

    def exists(self):
        raise NotImplementedError


@dataclass
class ExternalLocation(Location):
    storage: str
    stem: str
    suffix: str

    filename: Path | None
    qualname: str | None

    @classmethod
    def from_name(
        cls,
        name: str | None,
        *,
        context: AdapterContext | None = None,
        filename: Path | None = None,
    ):
        from inline_snapshot._global_state import state

        if not name:
            storage = state().config.default_storage
            stem = ""
            suffix = ""
        else:
            m = re.fullmatch(r"([0-9a-fA-F]{64}|[0-9a-fA-F]+\*)(\.[a-zA-Z0-9]+)", name)

            if m:
                storage = "hash"
                path = name
            elif ":" in name:
                storage, path = name.split(":", 1)
                if storage not in ("hash", "uuid"):
                    raise ValueError(f"storage has to be hash or uuid")
            else:
                storage = state().config.default_storage
                path = name

            if "." in path:
                stem, suffix = path.split(".", 1)
                suffix = "." + suffix
            elif not path:
                stem = ""
                suffix = ""
            else:
                raise ValueError(f"'{name}' is missing a suffix")

        qualname = None
        if context:
            filename = Path(context.file.filename)
            qualname = context.qualname

        return cls(storage, stem, suffix, filename, qualname)

    @property
    def path(self) -> str:
        return f"{self.stem or ''}{self.suffix or ''}"

    def to_str(self):
        return str(self)

    def __str__(self) -> str:
        return f"{self.storage}:{self.path}"

    def with_stem(self, new_stem):
        return dataclasses.replace(self, stem=new_stem)

    @contextmanager
    def load(self) -> Generator[Path]:
        from inline_snapshot._global_state import state

        assert self.storage

        storage = state().all_storages[self.storage]
        with storage.load(self) as file:
            yield file

    def store(self, new_file: Path):
        from inline_snapshot._global_state import state

        assert self.storage

        storage = state().all_storages[self.storage]
        storage.store(self, new_file)

    def delete(self):
        from inline_snapshot._global_state import state

        assert self.storage

        storage = state().all_storages[self.storage]
        storage.delete(self)

    def exists(self):
        return self.stem


class FileLocation(Location):
    def __init__(self, filename: Path):
        self._filename = filename

    @property
    def suffix(self):
        return self._filename.suffix

    def __str__(self) -> str:
        p = self._filename.resolve()

        try:
            p = p.relative_to(Path.cwd().resolve())
        except ValueError:
            pass

        return p.as_posix()

    @contextmanager
    def load(self) -> Generator[Path]:
        yield self._filename

    def store(self, new_file: Path):
        self._filename.parent.mkdir(exist_ok=True, parents=True)
        shutil.copy(new_file, self._filename)

    def exists(self):
        return self._filename.exists()
