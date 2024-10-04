from ._is import Is
from ._types import Snapshot

try:
    import dirty_equals  # type: ignore
except ImportError:  # pragma: no cover

    def is_dirty_equal(value):
        return False

else:

    def is_dirty_equal(value):
        return isinstance(value, dirty_equals.DirtyEquals) or (
            isinstance(value, type) and issubclass(value, dirty_equals.DirtyEquals)
        )


def update_allowed(value):
    return not (is_dirty_equal(value) or isinstance(value, (Is, Snapshot)))  # type: ignore


def is_unmanaged(value):
    return not update_allowed(value)


class Unmanaged:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        assert not isinstance(other, Unmanaged)

        return self.value == other


def map_unmanaged(value):
    if is_unmanaged(value):
        return Unmanaged(value)
    else:
        return value
