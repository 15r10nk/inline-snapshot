from __future__ import annotations

from pathlib import Path

from inline_snapshot._external._diff import BinaryDiff

from ._protocol import Format
from ._protocol import register_format


@register_format
class BinaryFormat(BinaryDiff, Format[bytes]):
    "Stores bytes in `.bin` files and shows them as a hexdump."

    suffix = ".bin"

    def is_format_for(self, value: object):
        return isinstance(value, bytes)

    def encode(self, value: bytes, path: Path):
        path.write_bytes(value)

    def decode(self, path: Path) -> bytes:
        return path.read_bytes()
