from __future__ import annotations

from typing import Any
from typing import Callable

custom_functions = []

from dataclasses import MISSING
from dataclasses import fields
from dataclasses import is_dataclass


def customize(f: Callable[[Any, Builder], Custom | None]):
    custom_functions.append(f)
    return f


class Custom:
    def map(self, f):
        raise NotImplementedError()


def get_handler(v, builder: Builder) -> Custom:
    for f in reversed(custom_functions):
        r = f(v, builder)
        if isinstance(r, Custom):
            return r

    return CustomValue(v)


class CustomDefault(Custom):
    def __init__(self, value):
        self.value = value


def unwrap_default(value):
    if isinstance(value, Default):
        return value.value
    return value


class CustomCall(Custom):
    def __init__(self, function, *args, **kwargs):
        """
        CustomCall(f,1,2,a=3).kwonly(b=4)
        """
        self._function = function
        self._args = args
        self._kwargs = kwargs
        self._kwonly = {}

    @property
    def args(self):
        return self._args

    @property
    def all_pos_args(self):
        return [*self._args, *self._kwargs.values()]

    @property
    def kwargs(self):
        return {**self._kwargs, **self._kwonly}

    def kwonly(self, **kwonly):
        assert not self._kwonly, "you should not call kwonly twice"
        assert (
            not kwonly.keys() & self._kwargs.keys()
        ), "same keys in kwargs and kwonly arguments"
        self._kwonly = kwonly
        return self

    def argument(self, pos_or_str):
        if isinstance(pos_or_str, int):
            return unwrap_default(self.all_pos_args[pos_or_str])
        else:
            return unwrap_default(self.kwargs[pos_or_str])

    def map(self, f):
        return self._function(
            *[f(unwrap_default(x)) for x in self._args],
            **{k: f(unwrap_default(v)) for k, v in self.kwargs.items()},
        )


class CustomList(Custom):
    def __init__(self, value) -> None:
        self.value = value

    def map(self, f):
        return [f(x) for x in self.value]


class CustomTuple(Custom):
    def __init__(self, value) -> None:
        self.value = value

    def map(self, f):
        return tuple([f(x) for x in self.value])


class CustomDict(Custom):
    def __init__(self, value) -> None:
        self.value = value

    def map(self, f):
        return {f(k): f(v) for k, v in self.value}


class CustomValue(Custom):
    def __init__(self, value, repr_str=None):

        if repr_str is None:
            self.repr_str = repr_str
        else:
            self.repr_str = repr(value)

        self.value = value

    def map(self, f):
        return self.value


@customize
def standard_handler(value, builder: Builder):
    if isinstance(value, list):
        return builder.List(value)

    if isinstance(value, tuple):
        return builder.Tuple(value)

    if isinstance(value, dict):
        return builder.Dict(value)


@customize
def dataclass_handler(value, builder: Builder):

    if is_dataclass(value):

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

        return builder.Call(type(value), [], kwargs)


try:
    import attrs
except ImportError:  # pragma: no cover
    pass
else:

    @customize
    def attrs_handler(value, builder: Builder):

        if attrs.has(value):

            kwargs = {}

            for field in attrs.fields(type(value)):
                if field.repr:
                    field_value = getattr(value, field.name)
                    is_default = False

                    if field.default is not attrs.NOTHING:

                        default_value = (
                            field.default
                            if not isinstance(field.default, attrs.Factory)
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

            return builder.Call(type(value), [], kwargs)


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

        if issubclass(value, BaseModel):

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

            return builder.Call(type(value), [], kwargs)


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
        type(value),
        [],
        {
            field: getattr(value, field)
            for field in value._fields
            if field not in value._field_defaults
            or getattr(value, field) != value._field_defaults[field]
        },
    )


@customize
def defaultdict_handler(value, builder: Builder):
    if issubclass(value, defaultdict):
        return CustomCall(
            type(value),
            [value.default_factory, dict(value)],
        )


class Builder:
    def List(self, value) -> CustomList:
        value = [get_handler(v, self) for v in value]
        return CustomList(value)

    def Tuple(self, value) -> CustomTuple:
        value = tuple([get_handler(v, self) for v in value])
        return CustomTuple(value)

    def Call(self, function, posonly_args, kwargs, kwonly_args) -> CustomCall:
        function = get_handler(function, self)
        posonly_args = [get_handler(arg, self) for arg in posonly_args]
        kwargs = {k: get_handler(arg, self) for k, arg in kwargs.items()}
        kwonly_args = {k: get_handler(arg, self) for k, arg in kwonly_args.items()}

        return CustomCall(function, *posonly_args, **kwargs).kwonly(**kwonly_args)

    def Default(self, value) -> CustomDefault:
        return CustomDefault(get_handler(value, self))

    def Dict(self, value) -> CustomDict:
        value = {get_handler(k, self): get_handler(v, self) for k, v in value.items()}
        return CustomDict(value)

    def Value(self, value, repr) -> CustomValue:
        return CustomValue(value, repr)
