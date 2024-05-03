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


@singledispatch
def code_repr_dispatch(v):
    return real_repr(v)


register_repr = code_repr_dispatch.register


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
