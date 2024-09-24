from ._is import Is
from ._types import Snapshot

try:
    import dirty_equals  # type: ignore
except ImportError:  # pragma: no cover

    def is_dirty_equal(value):
        return False

else:

    def is_dirty_equal(value):
        return isinstance(value, dirty_equals.DirtyEquals)


def update_allowed(value):
    return not is_dirty_equal(value) and not isinstance(value, (Is, Snapshot))
