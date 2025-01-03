from inline_snapshot._unmanaged import declare_unmanaged


@declare_unmanaged
class IsNormalized:
    def __init__(self, func, value) -> None:
        self._func = func
        self._value = value
        self._last_value = None

    def __eq__(self, other) -> bool:
        self._last_value = self._func(other)
        return self._last_value == self._value

    def __repr__(self):
        return f"IsNormalized({self._value}, should_be={self._last_value!r})"


def normalization(func):
    def f(value):
        return IsNormalized(func, value)

    return f
