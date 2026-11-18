from ._snapshot.snapshot_value import SnapshotValue


def is_snapshot(s: object) -> bool:
    """Return whether `s` is an inline snapshot wrapper.

    This function lets extension authors recognize snapshot objects without
    importing private implementation classes. It recognizes values returned by
    `snapshot()`, `snapshot_arg()`, and `snapshot()[key]`.

    When inline-snapshot is disabled, `snapshot()` and `snapshot_arg()` return
    their arguments unchanged, so ordinary values return `False`.
    External snapshots from `external()` and `external_file()` are not inline
    snapshot wrappers and return `False`.

    Args:
        s: The object to check.

    Returns:
        `True` if the object is an inline snapshot wrapper, otherwise `False`.
    """
    return isinstance(s, SnapshotValue)
