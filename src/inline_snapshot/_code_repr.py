from __future__ import annotations

import warnings
from contextlib import contextmanager
from functools import singledispatch
from typing import TYPE_CHECKING
from unittest import mock

from typing_extensions import deprecated

from inline_snapshot._generator_utils import only_value

if TYPE_CHECKING:
    from inline_snapshot._adapter_context import AdapterContext


real_repr = repr


class HasRepr:
    """This class is used for objects where `__repr__()` returns an non-
    parsable representation.

    HasRepr uses the type and repr of the value for equal comparison.

    You can change `__repr__()` to return valid python code or use
    `@customize_repr` to customize repr which is used by inline-
    snapshot.
    """

    def __init__(self, type, str_repr: str) -> None:
        self._type = type
        self._str_repr = str_repr

    def __repr__(self):
        return f"HasRepr({self._type.__qualname__}, {self._str_repr!r})"

    def __eq__(self, other):
        if isinstance(other, HasRepr):
            if other._type is not self._type:
                return False
        else:
            if type(other) is not self._type:
                return False

        with mock_repr(None):
            other_repr = value_code_repr(other)
        return other_repr == self._str_repr or other_repr == real_repr(self)


@singledispatch
def code_repr_dispatch(value):
    return real_repr(value)


@deprecated("use @customize instead")
def customize_repr(f):
    """Register a function which should be used to get the code representation
    of a object.

    ``` python
    @customize_repr
    def _(obj: MyCustomClass):
        return f"MyCustomClass(attr={repr(obj.attr)})"
    ```

    it is important to use `repr()` inside the implementation, because it is mocked to return the code representation

    you dont have to provide a custom implementation if:
    * __repr__() of your class returns a valid code representation,
    * and __repr__() uses `repr()` to get the representation of the child objects
    """
    warnings.warn(
        "@customize_repr is deprecated, @customize should be used instead",
        DeprecationWarning,
    )
    code_repr_dispatch.register(f)


def code_repr(obj):
    with mock_repr(None):
        return repr(obj)


@contextmanager
def mock_repr(context: AdapterContext):
    def new_repr(obj):
        from inline_snapshot._customize._builder import Builder

        return only_value(
            Builder(_snapshot_context=context)._get_handler(obj).repr(context)
        )

    with mock.patch("builtins.repr", new_repr):
        yield


def value_code_repr(obj):
    assert repr is not real_repr, "@mock_repr is missing"

    if not type(obj) == type(obj):  # pragma: no cover
        # this was caused by https://github.com/samuelcolvin/dirty-equals/issues/104
        # dispatch will not work in cases like this
        return (
            f"HasRepr({repr(type(obj))}, '< type(obj) can not be compared with == >')"
        )

    result = code_repr_dispatch(obj)

    return result
