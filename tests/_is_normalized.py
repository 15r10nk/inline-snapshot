from inline_snapshot._unmanaged import declare_unmanaged


@declare_unmanaged
class IsNormalized:
    def __init__(self, func, value) -> None:
        self._func = func
        self._value = value

    def __eq__(self, other) -> bool:
        return self._func(other) == self._value


def normalization(func):
    def f(value):
        return IsNormalized(func, value)

    return f
