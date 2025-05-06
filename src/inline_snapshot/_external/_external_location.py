from __future__ import annotations

import re
from dataclasses import dataclass


class HashError(Exception):
    pass


@dataclass()
class ExternalLocation:
    storage: str | None
    stem: str | None
    suffix: str | None

    @classmethod
    def from_name(cls, name: str | None):
        if name is None:
            return cls(None, None, None)

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

        return cls(storage, stem, suffix)

    @property
    def path(self) -> str:
        return f"{self.stem}{self.suffix or ''}"

    def to_str(self) -> str:
        return f"{self.storage}:{self.path}"
