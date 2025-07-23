from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Protocol
from typing import TypeVar

from rich.console import RenderableType

from inline_snapshot._exceptions import UsageError


def get_format_handler(data, suffix: str) -> Format:
    """
    Retrieves the appropriate format handler for the given data and suffix.

    Arguments:
        data: The data to be formatted.
        suffix: The suffix associated with the desired format.

    Returns:
        The format handler that matches the data and suffix.

    Raises:
        UsageError: If no format handler is found or if multiple handlers
        with the same priority exist for the given data and suffix.
    """
    from inline_snapshot._global_state import state

    if suffix:
        suffix = state().format_aliases.get(suffix, suffix)

    possible_formatter = sorted(
        [
            formatter
            for formatter in state().all_formats.values()
            if formatter.is_format_for(data)
            and (not suffix or suffix == formatter.suffix)
        ],
        key=lambda format: format.priority,
    )

    if not possible_formatter:
        and_suffix = f" and suffix '{suffix}'" if suffix else ""
        raise UsageError(
            f"No format handler found for the given type '{type(data).__qualname__}'{and_suffix}."
        )
    if (
        len(possible_formatter) >= 2
        and possible_formatter[-1].priority == possible_formatter[-2].priority
    ):
        and_suffix = f" and suffix '{suffix}'" if suffix else ""
        raise UsageError(
            f"Multiple format handlers found for the given type '{type(data).__qualname__}'. "
            f"The following handlers have the same priority: {[f.suffix for f in possible_formatter]}. "
            f"You can explicitly choose one with external('.suffix') or adjust the priorities of the handlers if you implemented them."
        )

    return possible_formatter[-1]


def get_format_handler_from_suffix(suffix: str) -> Format:
    """
    Retrieves the format handler associated with the given suffix.

    Arguments:
        suffix: The suffix for which the format handler is required.

    Returns:
        The format handler corresponding to the suffix.

    Raises:
        UsageError: If no format handler is found for the given suffix.
    """
    from inline_snapshot._global_state import state

    suffix = state().format_aliases.get(suffix, suffix)

    format = state().all_formats.get(suffix, None)

    if format is None:
        raise UsageError(f"Format '{suffix}' is unknown.")

    return format


T = TypeVar("T")


class Format(Protocol[T]):
    """
    Base class for the Format Protocol.
    """

    suffix: str
    """
    The suffix associated with this format handler.

    Every format implementation must define a suffix. This suffix is used
    when the external file is written and is required to find the correct
    format handler when the file is read again.
    """

    priority: int = 0
    """
    Determines the correct format when multiple format handlers can handle
    a given value (`is_format_for`).

    *priority* is `0` by default and can be set to a smaller number for
    generic formats that work with many data types (e.g., *.json*), where
    `is_format_for()` also returns `True` for `str` and `bytes`. This allows
    you to use `assert "text" == external()` without explicitly providing
    a `".txt"` suffix to distinguish it from `".json"`.

    A higher *priority* can be used for more specific formats, such as bytes
    with a `b"\\x89PNG"` prefix that should be stored as *.png* files.
    """

    def rich_diff(self, original: Path, new: Path) -> RenderableType:
        """
        Displays a diff between the original and new files.

        Arguments:
            original: The path to the original external file.
            new: The path to the new external file.

        Returns:
            A rich renderable object representing the diff. This can be a
            textual diff or another type of representation.
        """
        raise NotImplementedError

    def rich_show(self, path: Path) -> RenderableType:
        """
        Displays a representation of a newly created external object.

        Arguments:
            path: The path to the external file.

        Returns:
            A rich renderable object representing the new object. The
            representation should be concise.
        """
        raise NotImplementedError

    def is_format_for(self, value: object) -> bool:
        """
        Determines if this format handler can handle the given value.

        This function is used to find the correct format handler when no
        suffix is provided.

        ``` python
        assert value == external()
        ```

        Arguments:
            value: The value to be formatted.

        Returns:
            `True` if the value is handled by this format implementation.
        """
        raise NotImplementedError

    def encode(self, value: T, path: Path) -> None:
        """
        Converts the value and stores it in the specified path.

        Arguments:
            value: The value to be stored.
            path: The path to a temporary file where the value should be stored.
        """
        raise NotImplementedError

    def decode(self, path: Path) -> T:
        """
        Reads the value from the specified path.

        Arguments:
            path: The path to a temporary file where the value is stored.

        Returns:
            The value of the external object.
        """
        raise NotImplementedError


FormatT = TypeVar("FormatT")


def register_format(
    format: type[Format[FormatT]] | Format[FormatT] | None = None,
    *,
    replace_handler: bool = False,
):
    """
    Registers a new format handler for the suffix `format.suffix`.

    This function can also be used as a decorator:

    ``` python
    @register_format
    class MyFormat: ...
    ```

    which is equivalent to:

    ``` python
    register_format(MyFormat())
    ```

    Arguments:
        format: The format handler class or instance.
        replace_handler: If `True`, replaces an existing handler for the same suffix.

    Raises:
        UsageError: If a handler for the same suffix already exists and `replace_handler` is not set to `True`.
    """
    if format is None:
        return partial(register_format, replace_handler=replace_handler)

    from inline_snapshot._global_state import state

    instance = format() if isinstance(format, type) else format

    if not replace_handler and instance.suffix in state().all_formats:
        raise UsageError(
            f"A format handler is already registered for the suffix '{instance.suffix}'."
        )

    state().all_formats[instance.suffix] = instance
    return format


def register_format_alias(suffix: str, format: str):
    """
    Registers an alias for a given format suffix.

    Arguments:
        suffix: The suffix to register the alias for.
        format: The suffix of the format that should be used instead.

    Notes:
        The alias suffix is used to find the
        correct format handler.
    """
    from inline_snapshot._global_state import state

    state().format_aliases[suffix] = format
