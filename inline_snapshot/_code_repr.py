import ast
from enum import Enum
from enum import Flag
from functools import singledispatch
from unittest import mock

real_repr = repr


class HasRepr:
    """This class is used for objects where `__repr__()` returns an non
    parsable representation."""

    def __init__(self, str_repr: str) -> None:
        self._str_repr = str_repr

    def __repr__(self):
        return f"HasRepr({self._str_repr!r})"

    def __eq__(self, other):
        return code_repr(other) == self._str_repr


@singledispatch
def code_repr_dispatch(v):
    return real_repr(v)


def register_repr(f):
    """Register a funtion which should be used to get the code representation
    of a object.

    ```python
    @register_repr
    def _(obj: MyCustomClass):
        return f"MyCustomClass({repr(obj.attr)})"
    ```
    it is important to use `repr()` inside the implementation, because it is mocked to return the code represenation

    you dont have to provide a custom implementation if:
    * __repr__() of your class returns a valid code representation,
    * and __repr__() uses `repr()` to get the representaion of the child objects
    """
    code_repr_dispatch.register(f)


def code_repr(obj):
    with mock.patch("builtins.repr", code_repr_dispatch):
        result = code_repr_dispatch(obj)

    try:
        ast.parse(result)
    except SyntaxError:
        return real_repr(HasRepr(result))

    return result


@register_repr
def _(v: Enum):
    return str(v)


@register_repr
def _(v: Flag):
    name = type(v).__name__
    return " | ".join(str(flag) for flag in type(v) if flag in v)


@register_repr
def _(v: list):
    return "[" + ", ".join(map(repr, v)) + "]"


@register_repr
def _(v: set):
    if len(v) == 0:
        return "set()"

    return "{" + ", ".join(map(repr, v)) + "}"


@register_repr
def _(v: dict):
    return "{" + ", ".join(f"{repr(k)}:{repr(value)}" for k, value in v.items()) + "}"


@register_repr
def _(v: type):
    return v.__qualname__


try:
    from pydantic import BaseModel
except ImportError:
    pass
else:

    @register_repr
    def _(model: BaseModel):
        return (
            type(model).__name__
            + "("
            + ", ".join(
                e + "=" + repr(getattr(model, e)) for e in model.__pydantic_fields_set__
            )
            + ")"
        )
