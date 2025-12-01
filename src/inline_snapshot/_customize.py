from __future__ import annotations

import ast
from abc import ABC
from abc import abstractmethod
from collections import Counter
from collections import defaultdict
from pathlib import Path
from pathlib import PurePath
from types import BuiltinFunctionType
from types import FunctionType
from typing import Any
from typing import Callable

from inline_snapshot._code_repr import value_code_repr
from inline_snapshot._unmanaged import is_unmanaged
from inline_snapshot._utils import clone

custom_functions = []

from dataclasses import MISSING
from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields
from dataclasses import is_dataclass

from inline_snapshot._sentinels import undefined


def customize(f: Callable[[Any, Builder], Custom | None]):
    custom_functions.append(f)
    return f


class Custom(ABC):
    node_type: type[ast.AST] = ast.AST

    def __hash__(self):
        return hash(self.eval())

    def __eq__(self, other):
        assert isinstance(other, Custom)
        return self.eval() == other.eval()

    @abstractmethod
    def map(self, f):
        raise NotImplementedError()

    @abstractmethod
    def repr(self):
        raise NotImplementedError()

    def eval(self):
        return self.map(lambda a: a)


@dataclass(frozen=True)
class CustomDefault(Custom):
    value: Custom = field(compare=False)

    def repr(self):
        # this should never be called because default values are never converted into code
        assert False

    def map(self, f):
        return self.value.map(f)


@dataclass()
class CustomUnmanaged(Custom):
    value: Any

    def repr(self):
        return "<no repr>"

    def map(self, f):
        return f(self.value)


class CustomUndefined(Custom):
    def __init__(self):
        self.value = undefined

    def repr(self) -> str:
        return "..."

    def map(self, f):
        return f(undefined)


def unwrap_default(value):
    if isinstance(value, CustomDefault):
        return value.value
    return value


@dataclass(frozen=True)
class CustomCall(Custom):
    node_type = ast.Call
    _function: Custom = field(compare=False)
    _args: list[Custom] = field(compare=False)
    _kwargs: dict[str, Custom] = field(compare=False)
    _kwonly: dict[str, Custom] = field(default_factory=dict, compare=False)

    def repr(self) -> str:
        args = []
        args += [a.repr() for a in self.args]
        args += [
            f"{k}={v.repr()}"
            for k, v in self.kwargs.items()
            if not isinstance(v, CustomDefault)
        ]
        return f"{self._function.repr()}({', '.join(args)})"

    @property
    def args(self):
        return self._args

    @property
    def all_pos_args(self):
        return [*self._args, *self._kwargs.values()]

    @property
    def kwargs(self):
        return {**self._kwargs, **self._kwonly}

    def argument(self, pos_or_str):
        if isinstance(pos_or_str, int):
            return unwrap_default(self.all_pos_args[pos_or_str])
        else:
            return unwrap_default(self.kwargs[pos_or_str])

    def map(self, f):
        return self._function.map(f)(
            *[f(x.map(f)) for x in self._args],
            **{k: f(v.map(f)) for k, v in self.kwargs.items()},
        )


class CustomSequenceTypes:
    trailing_comma: bool
    braces: str
    value_type: type


@dataclass(frozen=True)
class CustomSequence(Custom, CustomSequenceTypes):
    value: list[Custom] = field(compare=False)

    def map(self, f):
        return f(self.value_type([x.map(f) for x in self.value]))

    def repr(self) -> str:
        trailing_comma = self.trailing_comma and len(self.value) == 1
        return f"{self.braces[0]}{', '.join(v.repr() for v in self.value)}{', ' if trailing_comma else ''}{self.braces[1]}"


class CustomList(CustomSequence):
    node_type = ast.List
    value_type = list
    braces = "[]"
    trailing_comma = False


class CustomTuple(CustomSequence):
    node_type = ast.Tuple
    value_type = tuple
    braces = "()"
    trailing_comma = True


@dataclass(frozen=True)
class CustomDict(Custom):
    node_type = ast.Dict
    value: dict[Custom, Custom] = field(compare=False)

    def map(self, f):
        return f({k.map(f): v.map(f) for k, v in self.value.items()})

    def repr(self) -> str:
        return (
            f"{{{ ', '.join(f'{k.repr()}: {v.repr()}' for k,v in self.value.items())}}}"
        )


class CustomValue(Custom):
    def __init__(self, value, repr_str=None):
        assert not isinstance(value, Custom)
        value = clone(value)

        if repr_str is None:
            self.repr_str = value_code_repr(value)
        else:
            self.repr_str = repr_str

        self.value = value

    def map(self, f):
        return f(self.value)

    def repr(self) -> str:
        return self.repr_str

    def __repr__(self):
        return f"CustomValue({self.repr_str})"


@customize
def standard_handler(value, builder: Builder):
    if isinstance(value, list):
        return builder.List(value)

    if type(value) is tuple:
        return builder.Tuple(value)

    if isinstance(value, dict):
        return builder.Dict(value)


@customize
def counter_handler(value, builder: Builder):
    if isinstance(value, Counter):
        return builder.Call(value, Counter, [dict(value)])


@customize
def function_handler(value, builder: Builder):
    if isinstance(value, FunctionType):
        return builder.Value(value, value.__qualname__)


@customize
def builtin_function_handler(value, builder: Builder):
    if isinstance(value, BuiltinFunctionType):
        return builder.Value(value, value.__name__)


@customize
def type_handler(value, builder: Builder):
    if isinstance(value, type):
        return builder.Value(value, value.__qualname__)


@customize
def path_handler(value, builder: Builder):
    if isinstance(value, Path):
        return builder.Call(value, Path, [value.as_posix()])

    if isinstance(value, PurePath):
        return builder.Call(value, PurePath, [value.as_posix()])


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


@customize
def set_handler(value, builder: Builder):
    if isinstance(value, set):
        if len(value) == 0:
            return builder.Value(value, "set()")
        else:
            return builder.Value(value, "{" + ", ".join(sort_set_values(value)) + "}")


@customize
def frozenset_handler(value, builder: Builder):
    if isinstance(value, frozenset):
        if len(value) == 0:
            return builder.Value(value, "frozenset()")
        else:
            return builder.Call(value, frozenset, [set(value)])


@customize
def dataclass_handler(value, builder: Builder):

    if is_dataclass(value) and not isinstance(value, type):

        kwargs = {}

        for field in fields(value):  # type: ignore
            if field.repr:
                field_value = getattr(value, field.name)
                is_default = False

                if field.default != MISSING and field.default == field_value:
                    is_default = True

                if (
                    field.default_factory != MISSING
                    and field.default_factory() == field_value
                ):
                    is_default = True

                if is_default:
                    field_value = builder.Default(field_value)
                kwargs[field.name] = field_value

        return builder.Call(value, type(value), [], kwargs, {})


try:
    import attrs
except ImportError:  # pragma: no cover
    pass
else:

    @customize
    def attrs_handler(value, builder: Builder):

        if attrs.has(type(value)):

            kwargs = {}

            for field in attrs.fields(type(value)):
                if field.repr:
                    field_value = getattr(value, field.name)
                    is_default = False

                    if field.default is not attrs.NOTHING:

                        default_value = (
                            field.default
                            if not isinstance(field.default, attrs.Factory)  # type: ignore
                            else (
                                field.default.factory()
                                if not field.default.takes_self
                                else field.default.factory(value)
                            )
                        )

                        if default_value == field_value:
                            is_default = True

                    if is_default:
                        field_value = builder.Default(field_value)

                    kwargs[field.name] = field_value

            return builder.Call(value, type(value), [], kwargs, {})


try:
    import pydantic
except ImportError:  # pragma: no cover
    pass
else:
    # import pydantic
    if pydantic.version.VERSION.startswith("1."):
        # pydantic v1
        from pydantic.fields import Undefined as PydanticUndefined  # type: ignore[attr-defined,no-redef]

        def get_fields(value):
            return value.__fields__

    else:
        # pydantic v2
        from pydantic_core import PydanticUndefined

        def get_fields(value):
            return type(value).model_fields

    from pydantic import BaseModel

    @customize
    def attrs_handler(value, builder: Builder):

        if isinstance(value, BaseModel):

            kwargs = {}

            for name, field in get_fields(value).items():  # type: ignore
                if getattr(field, "repr", True):
                    field_value = getattr(value, name)
                    is_default = False

                    if (
                        field.default is not PydanticUndefined
                        and field.default == field_value
                    ):
                        is_default = True

                    if (
                        field.default_factory is not None
                        and field.default_factory() == field_value
                    ):
                        is_default = True

                    if is_default:
                        field_value = builder.Default(field_value)

                    kwargs[name] = field_value

            return builder.Call(value, type(value), [], kwargs, {})


@customize
def namedtuple_handler(value, builder: Builder):
    t = type(value)
    b = t.__bases__
    if len(b) != 1 or b[0] != tuple:
        return
    f = getattr(t, "_fields", None)
    if not isinstance(f, tuple):
        return
    if not all(type(n) == str for n in f):
        return

    # TODO handle with builder.Default

    return builder.Call(
        value,
        type(value),
        [],
        {
            field: getattr(value, field)
            for field in value._fields
            if field not in value._field_defaults
            or getattr(value, field) != value._field_defaults[field]
        },
        {},
    )


@customize
def defaultdict_handler(value, builder: Builder):
    if isinstance(value, defaultdict):
        return builder.Call(
            value, type(value), [value.default_factory, dict(value)], {}, {}
        )


@customize
def unmanaged_handler(value, builder: Builder):
    if is_unmanaged(value):
        return CustomUnmanaged(value=value)


@customize
def undefined_handler(value, builder: Builder):
    if value is undefined:
        return CustomUndefined()


class Builder:
    def get_handler(self, v) -> Custom:
        if isinstance(v, Custom):
            return v

        for f in reversed(custom_functions):
            r = f(v, self)
            if isinstance(r, Custom):
                return r
        return CustomValue(v)

    def List(self, value) -> CustomList:
        custom = [self.get_handler(v) for v in value]
        return CustomList(value=custom)

    def Tuple(self, value) -> CustomTuple:
        custom = [self.get_handler(v) for v in value]
        return CustomTuple(value=custom)

    def Call(
        self, value, function, posonly_args=[], kwargs={}, kwonly_args={}
    ) -> CustomCall:
        function = self.get_handler(function)
        posonly_args = [self.get_handler(arg) for arg in posonly_args]
        kwargs = {k: self.get_handler(arg) for k, arg in kwargs.items()}
        kwonly_args = {k: self.get_handler(arg) for k, arg in kwonly_args.items()}

        return CustomCall(
            _function=function,
            _args=posonly_args,
            _kwargs=kwargs,
            _kwonly=kwonly_args,
        )

    def Default(self, value) -> CustomDefault:
        return CustomDefault(value=self.get_handler(value))

    def Dict(self, value) -> CustomDict:
        custom = {self.get_handler(k): self.get_handler(v) for k, v in value.items()}
        return CustomDict(value=custom)

    def Value(self, value, repr) -> CustomValue:
        return CustomValue(value, repr)
