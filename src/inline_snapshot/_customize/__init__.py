from __future__ import annotations

import ast
import importlib
from abc import ABC
from abc import abstractmethod
from collections import Counter
from collections import defaultdict
from dataclasses import MISSING
from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields
from dataclasses import is_dataclass
from dataclasses import replace
from pathlib import Path
from pathlib import PurePath
from types import BuiltinFunctionType
from types import FunctionType
from typing import Any
from typing import Callable
from typing import Optional
from typing import TypeAlias

from inline_snapshot._code_repr import HasRepr
from inline_snapshot._code_repr import value_code_repr
from inline_snapshot._customize._custom import CustomizeHandler
from inline_snapshot._sentinels import undefined
from inline_snapshot._unmanaged import is_dirty_equal
from inline_snapshot._unmanaged import is_unmanaged
from inline_snapshot._utils import clone

from ._custom import Custom
from ._custom import CustomizeHandler


def customize(f: CustomizeHandler) -> CustomizeHandler:
    """
    Registers a function as a customization hook inside inline-snapshot.

    Customization hooks allow you to control how objects are represented in snapshot code.
    When inline-snapshot generates code for a value, it calls each registered customization
    function in reverse order of registration until one returns a Custom object.

    **Important**: Customization handlers should be registered in your `conftest.py` file to ensure
    they are loaded before your tests run.

    Args:
        f: A customization handler function. See [CustomizeHandler][inline_snapshot._customize.CustomizeHandler]
            for the expected signature.

    Returns:
        The input function unchanged (for use as a decorator)

    Example:
        Basic usage with a custom class:

        <!-- inline-snapshot: create fix first_block outcome-failed=1 outcome-errors=1 -->
        ``` python
        from inline_snapshot import customize, snapshot


        class MyClass:
            def __init__(self, arg1, arg2, key=None):
                self.arg1 = arg1
                self.arg2 = arg2
                self.key_attr = key


        @customize
        def my_custom_handler(value, builder):
            if isinstance(value, MyClass):
                # Generate code like: MyClass(arg1, arg2, key=value)
                return builder.create_call(
                    MyClass, [value.arg1, value.arg2], {"key": value.key_attr}
                )
            return None  # Let other handlers process this value


        def test_myclass():
            obj = MyClass(42, "hello", key="world")
            assert obj == snapshot(MyClass(42, "hello", key="world"))
        ```

    Note:
        - **Always register handlers in `conftest.py`** to ensure they're available for all tests
        - Handlers are called in **reverse order** of registration (last registered is called first)
        - If no handler returns a Custom object, a default representation is used
        - Use builder methods (`create_call`, `create_list`, `create_dict`, etc.) to construct representations
        - Always return `None` if your handler doesn't apply to the given value type
        - The builder automatically handles recursive conversion of nested values

    See Also:
        - [Builder][inline_snapshot._customize.Builder]: Available builder methods
        - [Custom][inline_snapshot._customize.Custom]: Base class for custom representations
    """
    from inline_snapshot._global_state import state

    state().custom_functions.append(f)
    return f


@dataclass(frozen=True)
class CustomDefault(Custom):
    value: Custom = field(compare=False)

    def repr(self):
        # this should never be called because default values are never converted into code
        assert False

    def map(self, f):
        return self.value.map(f)

    def _needed_imports(self):
        yield from self.value._needed_imports()


@dataclass()
class CustomUnmanaged(Custom):
    value: Any

    def repr(self):
        return "'unmanaged'"  # pragma: no cover

    def map(self, f):
        return f(self.value)

    def _needed_imports(self):
        yield from ()


class CustomUndefined(Custom):
    def __init__(self):
        self.value = undefined

    def repr(self) -> str:
        return "..."

    def map(self, f):
        return f(undefined)

    def _needed_imports(self):
        yield from ()


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

    def _needed_imports(self):
        yield from self._function._needed_imports()
        for v in self._args:
            yield from v._needed_imports()

        for v in self._kwargs.values():
            yield from v._needed_imports()

        for v in self._kwonly.values():
            yield from v._needed_imports()


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

    def _needed_imports(self):
        for v in self.value:
            yield from v._needed_imports()


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

    def _needed_imports(self):
        for k, v in self.value.items():
            yield from k._needed_imports()
            yield from v._needed_imports()


class CustomValue(Custom):
    def __init__(self, value, repr_str=None):
        assert not isinstance(value, Custom)
        value = clone(value)
        self._imports = defaultdict(list)

        if repr_str is None:
            self.repr_str = value_code_repr(value)

            try:
                ast.parse(self.repr_str)
            except SyntaxError:
                self.repr_str = HasRepr(type(value), self.repr_str).__repr__()
                self.with_import("inline_snapshot", "HasRepr")
        else:
            self.repr_str = repr_str

        self.value = value

        super().__init__()

    def map(self, f):
        return f(self.value)

    def repr(self) -> str:
        return self.repr_str

    def __repr__(self):
        return f"CustomValue({self.repr_str})"

    def _needed_imports(self):
        yield from self._imports.items()

    def with_import(self, module, name, simplify=True):
        value = getattr(importlib.import_module(module), name)
        if simplify:
            parts = module.split(".")
            while len(parts) >= 2:
                if (
                    getattr(importlib.import_module(".".join(parts[:-1])), name, None)
                    == value
                ):
                    parts.pop()
                else:
                    break
            module = ".".join(parts)

        self._imports[module].append(name)

        return self


@customize
def standard_handler(value, builder: Builder):
    if isinstance(value, list):
        return builder.create_list(value)

    if type(value) is tuple:
        return builder.create_tuple(value)

    if isinstance(value, dict):
        return builder.create_dict(value)


@customize
def counter_handler(value, builder: Builder):
    if isinstance(value, Counter):
        return builder.create_call(Counter, [dict(value)])


@customize
def function_handler(value, builder: Builder):
    if isinstance(value, FunctionType):
        qualname = value.__qualname__
        name = qualname.split(".")[0]
        return builder.create_value(value, qualname).with_import(value.__module__, name)


@customize
def builtin_function_handler(value, builder: Builder):
    if isinstance(value, BuiltinFunctionType):
        return builder.create_value(value, value.__name__)


@customize
def type_handler(value, builder: Builder):
    if isinstance(value, type):
        qualname = value.__qualname__
        name = qualname.split(".")[0]
        return builder.create_value(value, qualname).with_import(value.__module__, name)


@customize
def path_handler(value, builder: Builder):
    if isinstance(value, Path):
        return builder.create_call(Path, [value.as_posix()])

    if isinstance(value, PurePath):
        return builder.create_call(PurePath, [value.as_posix()])


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
            return builder.create_value(value, "set()")
        else:
            return builder.create_value(
                value, "{" + ", ".join(sort_set_values(value)) + "}"
            )


@customize
def frozenset_handler(value, builder: Builder):
    if isinstance(value, frozenset):
        if len(value) == 0:
            return builder.create_value(value, "frozenset()")
        else:
            return builder.create_call(frozenset, [set(value)])


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
                    field_value = builder.create_default(field_value)
                kwargs[field.name] = field_value

        return builder.create_call(type(value), [], kwargs, {})


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
                        field_value = builder.create_default(field_value)

                    kwargs[field.name] = field_value

            return builder.create_call(type(value), [], kwargs, {})


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
                        field_value = builder.create_default(field_value)

                    kwargs[name] = field_value

            return builder.create_call(type(value), [], kwargs, {})


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

    return builder.create_call(
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
        return builder.create_call(
            type(value), [value.default_factory, dict(value)], {}, {}
        )


@customize
def unmanaged_handler(value, builder: Builder):
    if is_unmanaged(value):
        return CustomUnmanaged(value=value)


@customize
def undefined_handler(value, builder: Builder):
    if value is undefined:
        return CustomUndefined()


@customize
def dirty_equals_handler(value, builder: Builder):
    if is_dirty_equal(value) and builder._build_new_value:
        if isinstance(value, type):
            return builder.create_value(value, value.__name__)
        else:
            # TODO: args
            return builder.create_call(type(value))


@customize
def outsourced_handler(value, builder: Builder):
    from inline_snapshot._external._outsource import Outsourced

    if isinstance(value, Outsourced):
        return builder.create_value(value, repr(value)).with_import(
            "inline_snapshot", "external"
        )


@dataclass
class Builder:
    _build_new_value: bool = False

    def _get_handler(self, v) -> Custom:
        if isinstance(v, Custom):
            return v

        from inline_snapshot._global_state import state

        for f in reversed(state().custom_functions):
            r = f(v, self)
            if isinstance(r, Custom):
                break
        else:
            r = CustomValue(v)

        r.__dict__["original_value"] = v
        return r

    def create_list(self, value) -> Custom:
        """
        Creates an intermediate node for a list-expression which can be used as a result for your customization function.

        `create_list([1,2,3])` becomes `[1,2,3]` in the code.
        List elements are recursively converted into CustomNodes.
        """
        custom = [self._get_handler(v) for v in value]
        return CustomList(value=custom)

    def create_tuple(self, value) -> Custom:
        """
        Creates an intermediate node for a tuple-expression which can be used as a result for your customization function.

        `create_tuple((1, 2, 3))` becomes `(1, 2, 3)` in the code.
        Tuple elements are recursively converted into CustomNodes.
        """
        custom = [self._get_handler(v) for v in value]
        return CustomTuple(value=custom)

    def create_call(
        self, function, posonly_args=[], kwargs={}, kwonly_args={}
    ) -> Custom:
        """
        Creates an intermediate node for a function call expression which can be used as a result for your customization function.

        `create_call(MyClass, [arg1, arg2], {'key': value})` becomes `MyClass(arg1, arg2, key=value)` in the code.
        Function, arguments, and keyword arguments are recursively converted into CustomNodes.
        """
        function = self._get_handler(function)
        posonly_args = [self._get_handler(arg) for arg in posonly_args]
        kwargs = {k: self._get_handler(arg) for k, arg in kwargs.items()}
        kwonly_args = {k: self._get_handler(arg) for k, arg in kwonly_args.items()}

        return CustomCall(
            _function=function,
            _args=posonly_args,
            _kwargs=kwargs,
            _kwonly=kwonly_args,
        )

    def create_default(self, value) -> Custom:
        """
        Creates an intermediate node for a default value which can be used as a result for your customization function.

        Default values are not included in the generated code when they match the actual default.
        The value is recursively converted into a CustomNode.
        """
        return CustomDefault(value=self._get_handler(value))

    def create_dict(self, value) -> Custom:
        """
        Creates an intermediate node for a dict-expression which can be used as a result for your customization function.

        `create_dict({'key': 'value'})` becomes `{'key': 'value'}` in the code.
        Dict keys and values are recursively converted into CustomNodes.
        """
        custom = {self._get_handler(k): self._get_handler(v) for k, v in value.items()}
        return CustomDict(value=custom)

    def create_value(self, value, repr: str | None = None) -> CustomValue:
        """
        Creates an intermediate node for a value with a custom representation which can be used as a result for your customization function.

        `create_value(my_obj, 'MyClass')` becomes `MyClass` in the code.
        Use this when you want to control the exact string representation of a value.
        """
        return CustomValue(value, repr)
