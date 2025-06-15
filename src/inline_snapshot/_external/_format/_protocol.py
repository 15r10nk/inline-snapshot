from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Protocol
from typing import TypeVar

from inline_snapshot._exceptions import UsageError


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
        and_suffix = f" and suffix '{suffix}'" if suffix else ""
        raise UsageError(
            f"found no format handler for the given type '{type(data).__qualname__}'{and_suffix}."
        )


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


def register_format_alias(suffix, format_suffix):
    from inline_snapshot._global_state import state

    state().format_aliases[suffix] = format_suffix
