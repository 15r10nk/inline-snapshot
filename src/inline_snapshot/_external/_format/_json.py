from __future__ import annotations

import json
from pathlib import Path

from inline_snapshot._external._diff import TextDiff

from ._protocol import Format
from ._protocol import register_format


def is_json(obj):
    if isinstance(obj, (int, str, bool, float, type(None))):
        return True
    if isinstance(obj, dict) and all(
        is_json(v) and isinstance(k, str) for k, v in obj.items()
    ):
        return True
    if isinstance(obj, list) and all(is_json(v) for v in obj):
        return True
    return False


@register_format
class JsonFormat(TextDiff, Format[object]):
    "Stores the data with `json.dump()`."

    suffix = ".json"
    priority = -10

    def is_format_for(self, value: object):
        return is_json(value)

    def encode(self, value: object, path: Path):

        with path.open("w", newline="\n", encoding="utf-8") as f:
            json.dump(value, f, indent=2)

    def decode(self, path: Path) -> object:

        with path.open("r", newline="\n", encoding="utf-8") as f:
            return json.load(f)
