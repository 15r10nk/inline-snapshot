from ._external._external_base import ExternalBase
from ._snapshot.snapshot_value import SnapshotValue


def is_snapshot(s: object) -> bool:
    """Return whether `s` is a snapshot wrapper.

    This function lets extension authors recognize snapshot objects without
    importing private implementation classes. It recognizes values returned by
    `snapshot()`, `snapshot_arg()`, `snapshot()[key]`, `external()`, and
    `external_file()`.

    When inline-snapshot is disabled, snapshot functions return ordinary values
    instead of wrappers, so those values return `False`.
    Comparison values wrapped with `Is()` or `outsource()` return `False`.

    Args:
        s: The object to check.

    Returns:
        `True` if the object is a snapshot wrapper, otherwise `False`.
    """
    return isinstance(s, (SnapshotValue, ExternalBase))
