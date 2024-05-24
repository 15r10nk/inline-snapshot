import ast
from enum import Enum
from enum import Flag
from functools import singledispatch
from unittest import mock

real_repr = repr


class HasRepr:
    """This class is used for objects where `__repr__()` returns an non
    parsable representation."""

    def __init__(self, type, str_repr: str) -> None:
        self._type = type
        self._str_repr = str_repr

    def __repr__(self):
        return f"HasRepr({self._type.__qualname__}, {self._str_repr!r})"

    def __eq__(self, other):
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
    with mock.patch("builtins.repr", code_repr):
        result = code_repr_dispatch(obj)

    try:
        ast.parse(result)
    except SyntaxError:
        return real_repr(HasRepr(type(obj), result))

    return result


@register_repr
def _(v: Enum):
    return f"{type(v).__qualname__}.{v.name}"


@register_repr
def _(v: Flag):
    name = type(v).__qualname__
    return " | ".join(f"{name}.{flag.name}" for flag in type(v) if flag in v)


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


from dataclasses import is_dataclass, fields
from abc import ABC


class IsDataclass(ABC):
    @staticmethod
    def __subclasshook__(subclass):
        return is_dataclass(subclass)


@register_repr
def _(v: IsDataclass):
    attrs = []
    for field in fields(v):  # type: ignore
        if field.repr:
            value = getattr(v, field.name)
            attrs.append(f"{field.name} = {repr(value)}")

    return f"{repr(type(v))}({', '.join(attrs)})"


try:
    from pydantic import BaseModel
except ImportError:  # pragma: no cover
    pass
else:

    @register_repr
    def _(model: BaseModel):
        return (
            type(model).__qualname__
            + "("
            + ", ".join(
                e + "=" + repr(getattr(model, e))
                for e in sorted(model.__pydantic_fields_set__)
            )
            + ")"
        )
