from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass
from pathlib import Path

from inline_snapshot._adapter.adapter import AdapterContext


@dataclass
class ExternalLocation:
    storage: str | None
    stem: str | None
    suffix: str | None

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
        if name is None:
            return cls("hash", None, None, None, None)

        m = re.fullmatch(r"([0-9a-fA-F]*)\*?(\.[a-zA-Z0-9]*)", name)

        if m:
            storage = "hash"
            path = name
        elif ":" in name:
            storage, path = name.split(":", 1)
        else:
            raise ValueError(
                "path has to be of the form <hash>.<suffix> or <partial_hash>*.<suffix>"
            )

        if "." in path:
            stem, suffix = path.split(".", 1)
            suffix = "." + suffix
        else:
            stem = path
            suffix = None

        qualname = None
        if context:
            filename = Path(context.file.filename)
            qualname = context.qualname

        return cls(storage, stem, suffix, filename, qualname)

    @property
    def path(self) -> str:
        return f"{self.stem or ''}{self.suffix or ''}"

    def to_str(self) -> str:
        if self.storage:
            return f"{self.storage}:{self.path}"
        else:
            return self.path

    def with_stem(self, new_stem):
        return dataclasses.replace(self, stem=new_stem)
