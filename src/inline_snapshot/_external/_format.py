from __future__ import annotations

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

    @classmethod
    def rich_diff(cls, original: Path, new: Path):
        raise NotImplementedError

    @classmethod
    def rich_show(cls, path: Path):
        raise NotImplementedError

    @classmethod
    def handle(cls, data: object):
        raise NotImplementedError

    @classmethod
    def encode(cls, value: T, path: Path):
        raise NotImplementedError

    @classmethod
    def decode(cls, path: Path) -> T:
        raise NotImplementedError


FormatT = TypeVar("FormatT")


def register_format(format: type[Format[FormatT]] | Format[FormatT]):
    from inline_snapshot._global_state import state

    instance = format() if isinstance(format, type) else format
    state().all_formats[instance.suffix] = instance
    return format


@register_format
class BinaryFormat(BinaryDiff, Format[bytes]):
    "stores bytes in `.bin` files and shows them as hexdump"

    suffix = ".bin"

    @classmethod
    def handle(cls, data: object):
        return isinstance(data, bytes)

    @classmethod
    def encode(cls, value: bytes, path: Path):
        path.write_bytes(value)

    @classmethod
    def decode(cls, path: Path) -> bytes:
        return path.read_bytes()


@register_format
class TextFormat(TextDiff, Format):
    "stores strings in `.txt` files"

    suffix = ".txt"

    @classmethod
    def handle(cls, data: object):
        return isinstance(data, str)

    @classmethod
    def encode(cls, value: str, path: Path):
        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(value)

    @classmethod
    def decode(cls, path: Path) -> str:
        with path.open("r", encoding="utf-8", newline="\n") as f:
            return f.read()


@register_format
class JsonFormat(TextDiff, Format[object]):
    "stores the data with `json.dump()`"

    suffix = ".json"
    suffix_required = True

    @classmethod
    def handle(cls, data: object):
        return True

    @classmethod
    def encode(cls, value: object, path: Path):
        import json

        with path.open("w", newline="\n", encoding="utf-8") as f:
            json.dump(value, f, indent=2)

    @classmethod
    def decode(cls, path: Path) -> object:
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
