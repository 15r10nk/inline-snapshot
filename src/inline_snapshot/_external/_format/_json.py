from __future__ import annotations

import json
from pathlib import Path

from inline_snapshot._external._diff import TextDiff

from ._protocol import Format
from ._protocol import register_format


@register_format
class JsonFormat(TextDiff, Format[object]):
    "stores the data with `json.dump()`"

    suffix = ".json"
    suffix_required = True

    def handle(self, data: object):
        return True

    def encode(self, value: object, path: Path):

        with path.open("w", newline="\n", encoding="utf-8") as f:
            json.dump(value, f, indent=2)

    def decode(self, path: Path) -> object:

        with path.open("r", newline="\n", encoding="utf-8") as f:
            return json.load(f)
