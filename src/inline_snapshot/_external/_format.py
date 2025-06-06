from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Protocol
from typing import TypeVar

from inline_snapshot._exceptions import UsageError
from inline_snapshot._external._diff import BinaryDiff
from inline_snapshot._external._diff import TextDiff


def get_format_handler(data, suffix: str | None) -> Format:
    from inline_snapshot._global_state import state

    if suffix is not None:
        suffix = state().format_aliases.get(suffix, suffix)

    for formatter in state().all_formats.values():
        if formatter.handle(data) and (
            suffix == formatter.suffix
            if formatter.suffix_required
            else (suffix is None or suffix == formatter.suffix)
        ):
            return formatter
    else:
        raise UsageError("data has to be of type bytes | str")


def get_format_handler_from_suffix(suffix: str) -> Format:
    from inline_snapshot._global_state import state

    suffix = state().format_aliases.get(suffix, suffix)

    format = state().all_formats.get(suffix, None)

    if format is None:
        raise UsageError(f"format '{suffix}' is unknown")

    return format


T = TypeVar("T")


class Format(Protocol[T]):
    suffix: str
    suffix_required: bool = False

    def rich_diff(self, original: Path, new: Path):
        raise NotImplementedError

    def rich_show(self, path: Path):
        raise NotImplementedError

    def handle(self, data: object):
        raise NotImplementedError

    def encode(self, value: T, path: Path):
        raise NotImplementedError

    def decode(self, path: Path) -> T:
        raise NotImplementedError


FormatT = TypeVar("FormatT")


def register_format(
    format: type[Format[FormatT]] | Format[FormatT] | None = None,
    *,
    replace_handler=False,
):

    if format is None:
        return partial(register_format, replace_handler=replace_handler)

    from inline_snapshot._global_state import state

    instance = format() if isinstance(format, type) else format

    if not replace_handler and instance.suffix in state().all_formats:
        raise UsageError(
            f"Two format handlers cannot be registered for the same suffix '{instance.suffix}'."
        )

    state().all_formats[instance.suffix] = instance
    return format


@register_format
class BinaryFormat(BinaryDiff, Format[bytes]):
    "stores bytes in `.bin` files and shows them as hexdump"

    suffix = ".bin"

    def handle(self, data: object):
        return isinstance(data, bytes)

    def encode(self, value: bytes, path: Path):
        path.write_bytes(value)

    def decode(self, path: Path) -> bytes:
        return path.read_bytes()


@register_format
class TextFormat(TextDiff, Format):
    "stores strings in `.txt` files"

    suffix = ".txt"

    def handle(self, data: object):
        return isinstance(data, str)

    def encode(self, value: str, path: Path):
        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(value)

    def decode(self, path: Path) -> str:
        with path.open("r", encoding="utf-8", newline="\n") as f:
            return f.read()


@register_format
class JsonFormat(TextDiff, Format[object]):
    "stores the data with `json.dump()`"

    suffix = ".json"
    suffix_required = True

    def handle(self, data: object):
        return True

    def encode(self, value: object, path: Path):
        import json

        with path.open("w", newline="\n", encoding="utf-8") as f:
            json.dump(value, f, indent=2)

    def decode(self, path: Path) -> object:
        import json

        with path.open("r", newline="\n", encoding="utf-8") as f:
            return json.load(f)


# @register_format
# class PickleFormat(Format):
#     suffix = ".pickle"
#     suffix_required = True
#     diff = "binary"

#     @staticmethod
#     def handle(data):
#         return True

#     @staticmethod
#     def encode(value: object, path: Path):
#         import pickle

#         with path.open("wb") as f:
#             pickle.dump(value, f, protocol=5)

#     @staticmethod
#     def decode(path: Path) -> typing.Any:
#         import pickle

#         with path.open("rb") as f:
#             return pickle.load(f)


def register_format_alias(suffix, format_suffix):
    from inline_snapshot._global_state import state

    state().format_aliases[suffix] = format_suffix
