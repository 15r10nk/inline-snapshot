from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Protocol
from typing import TypeVar

from rich.console import RenderableType

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
    """
    Base class for the Format Protocol.
    """

    suffix: str
    """
    The suffix which is associated with this format handler.
    """

    suffix_required: bool = False
    """
    should be `True` when this format handles many different datatypes which are also handled by other formats (like `.json`).
    """

    def rich_diff(self, original: Path, new: Path) -> RenderableType:
        """
        called to show a diff of both files.

        Arguments:
            original: The path to the original external file used until now.
            new: The path to the new external file.

        Returns:
            An rich renderable
        """
        raise NotImplementedError

    def rich_show(self, path: Path) -> RenderableType:
        """

        Arguments:
            path: The path to the external file.

        Returns:
            An rich renderable
        """
        raise NotImplementedError

    def isHandled(self, value: object) -> bool:
        """
        This function is used to find the correct format handler for cases like this.
        ``` python
        assert value == external()
        ```

        Arguments:
            value: the value to be formatted

        Returns:
            `True` if value is handled by this format implementation.
        """
        raise NotImplementedError

    def encode(self, value: T, path: Path) -> None:
        """
        Convert the value and store it in the given path.
        Arguments:
            value: The value which should be stored.
            path: path to a temporary file where this value should be stored.
        """
        raise NotImplementedError

    def decode(self, path: Path) -> T:
        """
        Read the value from the given path.

        Arguments:
            path: path to a temporary file where this value is stored.

        Returns:
            The value of this external object.
        """
        raise NotImplementedError


FormatT = TypeVar("FormatT")


def register_format(
    format: type[Format[FormatT]] | Format[FormatT] | None = None,
    *,
    replace_handler: bool = False,
):
    """
    Registers a new format handler for `format.suffix`.

    Arguments:
        format: the format handler class or instance
        replace_handler: will replace an existing handler if set to true.
    """

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


def register_format_alias(suffix: str, format: str):
    """
    Registers an alias format for a given suffix:

    Arguments:
        suffix: The suffix you want to register the alias for.
        format: The suffix of the format which should be used instead.
            This suffix is not used for filenames which are stored, but only to find the correct format handler.
    """
    from inline_snapshot._global_state import state

    state().format_aliases[suffix] = format
