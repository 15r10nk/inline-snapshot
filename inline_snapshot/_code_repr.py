import ast
from abc import ABC
from collections import defaultdict
from dataclasses import fields
from dataclasses import is_dataclass
from dataclasses import MISSING
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
    """Register a funtion which should be used to get the code representation
    of a object.

    ```python
    @customize_repr
    def _(obj: MyCustomClass):
        return f"MyCustomClass(attr={repr(obj.attr)})"
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


# -8<- [start:Enum]
@customize_repr
def _(value: Enum):
    return f"{type(value).__qualname__}.{value.name}"


# -8<- [end:Enum]


@customize_repr
def _(value: Flag):
    name = type(value).__qualname__
    return " | ".join(f"{name}.{flag.name}" for flag in type(value) if flag in value)


# -8<- [start:list]
@customize_repr
def _(value: list):
    return "[" + ", ".join(map(repr, value)) + "]"


# -8<- [end:list]


class OnlyTuple(ABC):
    _inline_snapshot_name = "builtins.tuple"

    @classmethod
    def __subclasshook__(cls, t):
        return t is tuple


@customize_repr
def _(value: OnlyTuple):
    assert isinstance(value, tuple)
    if len(value) == 1:
        return f"({repr(value[0])},)"
    return "(" + ", ".join(map(repr, value)) + ")"


class IsNamedTuple(ABC):
    _inline_snapshot_name = "namedtuple"

    _fields: tuple
    _field_defaults: dict

    @classmethod
    def __subclasshook__(cls, t):
        b = t.__bases__
        if len(b) != 1 or b[0] != tuple:
            return False
        f = getattr(t, "_fields", None)
        if not isinstance(f, tuple):
            return False
        return all(type(n) == str for n in f)


@customize_repr
def _(value: IsNamedTuple):
    params = ", ".join(
        f"{field}={repr(getattr(value,field))}"
        for field in value._fields
        if field not in value._field_defaults
        or getattr(value, field) != value._field_defaults[field]
    )
    return f"{repr(type(value))}({params})"


@customize_repr
def _(value: set):
    if len(value) == 0:
        return "set()"

    return "{" + ", ".join(map(repr, value)) + "}"


@customize_repr
def _(value: frozenset):
    if len(value) == 0:
        return "frozenset()"

    return "frozenset({" + ", ".join(map(repr, value)) + "})"


@customize_repr
def _(value: dict):
    result = (
        "{" + ", ".join(f"{repr(k)}: {repr(value)}" for k, value in value.items()) + "}"
    )

    if type(value) is not dict:
        result = f"{repr(type(value))}({result})"

    return result


@customize_repr
def _(value: defaultdict):
    return f"defaultdict({repr(value.default_factory)}, {repr(dict(value))})"


@customize_repr
def _(value: type):
    return value.__qualname__


class IsDataclass(ABC):
    _inline_snapshot_name = "dataclass"

    @classmethod
    def __subclasshook__(cls, subclass):
        return is_dataclass(subclass)


@customize_repr
def _(value: IsDataclass):
    attrs = []
    for field in fields(value):  # type: ignore
        if field.repr:
            field_value = getattr(value, field.name)

            if field.default != MISSING and field.default == field_value:
                continue

            if (
                field.default_factory != MISSING
                and field.default_factory() == field_value
            ):
                continue

            attrs.append(f"{field.name}={repr(field_value)}")

    return f"{repr(type(value))}({', '.join(attrs)})"


try:
    from pydantic import BaseModel
except ImportError:  # pragma: no cover
    pass
else:

    @customize_repr
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
