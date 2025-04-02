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
    global unmanaged_types
    return not (is_dirty_equal(value) or isinstance(value, tuple(unmanaged_types)))  # type: ignore


unmanaged_types = [Is, Snapshot]


def is_unmanaged(value):
    return not update_allowed(value)


def declare_unmanaged(data_type):
    global unmanaged_types
    unmanaged_types.append(data_type)
    return data_type


class Unmanaged:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        assert not isinstance(other, Unmanaged)

        return self.value == other

    def __repr__(self):
        return repr(self.value)


def map_unmanaged(value):
    if is_unmanaged(value):
        return Unmanaged(value)
    else:
        return value
