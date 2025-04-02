import ast
from enum import Enum
from enum import Flag
from functools import singledispatch
from unittest import mock

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

        other_repr = code_repr(other)
        return other_repr == self._str_repr or other_repr == repr(self)


def used_hasrepr(tree):
    return [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "HasRepr"
        and len(n.args) == 2
    ]


@singledispatch
def code_repr_dispatch(value):
    return real_repr(value)


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
    code_repr_dispatch.register(f)


def code_repr(obj):

    with mock.patch("builtins.repr", mocked_code_repr):
        return mocked_code_repr(obj)


def mocked_code_repr(obj):
    from inline_snapshot._adapter.adapter import get_adapter_type

    adapter = get_adapter_type(obj)
    assert adapter is not None
    return adapter.repr(obj)


def value_code_repr(obj):
    if not type(obj) == type(obj):  # pragma: no cover
        # this was caused by https://github.com/samuelcolvin/dirty-equals/issues/104
        # dispatch will not work in cases like this
        return (
            f"HasRepr({repr(type(obj))}, '< type(obj) can not be compared with == >')"
        )

    result = code_repr_dispatch(obj)

    try:
        ast.parse(result)
    except SyntaxError:
        return real_repr(HasRepr(type(obj), result))

    return result


# -8<- [start:Enum]
@customize_repr
def _(value: Enum):
    return f"{type(value).__qualname__}.{value.name}"


# -8<- [end:Enum]


@customize_repr
def _(value: Flag):
    name = type(value).__qualname__
    return " | ".join(f"{name}.{flag.name}" for flag in type(value) if flag in value)


def sort_set_values(set_values):
    is_sorted = False
    try:
        set_values = sorted(set_values)
        is_sorted = True
    except TypeError:
        pass

    set_values = list(map(repr, set_values))
    if not is_sorted:
        set_values = sorted(set_values)

    return set_values


@customize_repr
def _(value: set):
    if len(value) == 0:
        return "set()"

    return "{" + ", ".join(sort_set_values(value)) + "}"


@customize_repr
def _(value: frozenset):
    if len(value) == 0:
        return "frozenset()"

    return "frozenset({" + ", ".join(sort_set_values(value)) + "})"


@customize_repr
def _(value: type):
    return value.__qualname__
