from ._global_state import state

try:
    import dirty_equals  # type: ignore
except ImportError:  # pragma: no cover

    def is_dirty_equal(value):
        return False

else:

    def is_dirty_equal(value):
        t = value if isinstance(value, type) else type(value)
        return any(x is dirty_equals.DirtyEquals for x in t.__mro__)


def update_allowed(value):
    return not (is_dirty_equal(value) or isinstance(value, tuple(state().unmanaged_types)))  # type: ignore


def is_unmanaged(value):
    return not update_allowed(value)


def declare_unmanaged(data_type):
    if (
        data_type is int
        or data_type is str
        or data_type is float
        or data_type is complex
        or data_type is bool
        or data_type is bytes
        or data_type is type(None)
        or data_type is type(Ellipsis)
    ):
        raise TypeError(f"{data_type.__name__} cannot be declared unmanaged")
    state().unmanaged_types.append(data_type)
    return data_type
