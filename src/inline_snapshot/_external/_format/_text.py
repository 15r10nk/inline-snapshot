from __future__ import annotations

from pathlib import Path

from inline_snapshot._external._diff import TextDiff

from ._protocol import Format
from ._protocol import register_format


@register_format
class TextFormat(TextDiff, Format[str]):
    "Stores strings in `.txt` files."

    suffix = ".txt"

    def is_format_for(self, value: object):
        return isinstance(value, str)

    def encode(self, value: str, path: Path):
        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(value)

    def decode(self, path: Path) -> str:
        with path.open("r", encoding="utf-8", newline="\n") as f:
            return f.read()
