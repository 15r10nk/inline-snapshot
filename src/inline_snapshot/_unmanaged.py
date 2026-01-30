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
    global unmanaged_types
    return not (is_dirty_equal(value) or isinstance(value, tuple(unmanaged_types)))  # type: ignore


unmanaged_types = []


def is_unmanaged(value):
    return not update_allowed(value)


def declare_unmanaged(data_type):
    global unmanaged_types
    unmanaged_types.append(data_type)
    return data_type
