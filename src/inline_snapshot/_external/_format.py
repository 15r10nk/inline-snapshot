from __future__ import annotations

import typing

from inline_snapshot._exceptions import UsageError


def get_format_handler(data, suffix: str | None) -> type[Format]:
    from inline_snapshot._global_state import state

    if suffix is not None:
        suffix = state().format_aliases.get(suffix, suffix)

    for formatter in state().all_formats:
        if formatter.handle(data) and (suffix is None or suffix == formatter.suffix):
            return formatter
    else:
        raise UsageError("data has to be of type bytes | str")


def get_format_handler_from_suffix(suffix: str) -> type[Format] | None:
    from inline_snapshot._global_state import state

    suffix = state().format_aliases.get(suffix, suffix)

    for formatter in state().all_formats:
        if formatter.suffix == suffix:
            return formatter
    return None


class Format:

    suffix: str

    @staticmethod
    def handle(data):
        raise NotImplementedError

    @staticmethod
    def encode(value, file):
        raise NotImplementedError

    @staticmethod
    def decode(file):
        raise NotImplementedError


def register_format(cls):
    from inline_snapshot._global_state import state

    state().all_formats.append(cls)
    return cls


@register_format
class BinFormat(Format):
    suffix = ".bin"

    @staticmethod
    def handle(data):
        return isinstance(data, bytes)

    @staticmethod
    def encode(value: bytes, file: typing.BinaryIO):
        file.write(value)

    @staticmethod
    def decode(file: typing.BinaryIO) -> bytes:
        return file.read()


@register_format
class TxtFormat(Format):
    suffix = ".txt"

    @staticmethod
    def handle(data):
        return isinstance(data, str)

    @staticmethod
    def encode(value: str, file: typing.BinaryIO):
        file.write(value.encode("utf-8"))

    @staticmethod
    def decode(file: typing.BinaryIO) -> str:
        return file.read().decode("utf-8")


def txt_like_suffix(suffix):
    from inline_snapshot._global_state import state

    state().format_aliases[suffix] = ".txt"
