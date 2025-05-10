from __future__ import annotations

import typing
from pathlib import Path

from inline_snapshot._exceptions import UsageError


def get_format_handler(data, suffix: str | None) -> type[Format]:
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


def get_format_handler_from_suffix(suffix: str) -> type[Format] | None:
    from inline_snapshot._global_state import state

    suffix = state().format_aliases.get(suffix, suffix)

    return state().all_formats.get(suffix, None)


class Format:

    suffix: str
    suffix_required = False

    @staticmethod
    def handle(data):
        raise NotImplementedError

    @staticmethod
    def encode(value, path: Path):
        raise NotImplementedError

    @staticmethod
    def decode(path: Path):
        raise NotImplementedError


def register_format(cls):
    from inline_snapshot._global_state import state

    state().all_formats[cls.suffix] = cls
    return cls


@register_format
class BinFormat(Format):
    suffix = ".bin"

    @staticmethod
    def handle(data):
        return isinstance(data, bytes)

    @staticmethod
    def encode(value: bytes, path: Path):
        path.write_bytes(value)

    @staticmethod
    def decode(path: Path) -> bytes:
        return path.read_bytes()


@register_format
class TxtFormat(Format):
    suffix = ".txt"

    @staticmethod
    def handle(data):
        return isinstance(data, str)

    @staticmethod
    def encode(value: str, path: Path):
        path.write_text(value, encoding="utf-8")

    @staticmethod
    def decode(path: Path) -> str:
        return path.read_text(encoding="utf-8")


@register_format
class JsonFormat(Format):
    suffix = ".json"
    suffix_required = True

    @staticmethod
    def handle(data):
        return True

    @staticmethod
    def encode(value: object, path: Path):
        import json

        with path.open("w") as f:
            json.dump(value, f, indent=2)

    @staticmethod
    def decode(path: Path) -> str:
        import json

        with path.open("r") as f:
            return json.load(f)


@register_format
class PickleFormat(Format):
    suffix = ".pickle"
    suffix_required = True

    @staticmethod
    def handle(data):
        return True

    @staticmethod
    def encode(value: object, path: Path):
        import pickle

        with path.open("wb") as f:
            pickle.dump(value, f, protocol=5)

    @staticmethod
    def decode(path: Path) -> typing.Any:
        import pickle

        with path.open("rb") as f:
            return pickle.load(f)


def register_format_alias(suffix, format_suffix):
    from inline_snapshot._global_state import state

    state().format_aliases[suffix] = format_suffix
