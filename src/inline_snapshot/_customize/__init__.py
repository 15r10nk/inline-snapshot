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
from functools import partial
from pathlib import Path
from pathlib import PurePath
from types import BuiltinFunctionType
from types import FunctionType
from typing import Any
from typing import Callable
from typing import Generator
from typing import Optional
from typing import TypeAlias
from typing import overload

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._change import Change
from inline_snapshot._change import ChangeBase
from inline_snapshot._change import ExternalChange
from inline_snapshot._code_repr import HasRepr
from inline_snapshot._code_repr import value_code_repr
from inline_snapshot._compare_context import compare_context
from inline_snapshot._compare_context import compare_only
from inline_snapshot._customize._custom import CustomizeHandler
from inline_snapshot._external._external_location import ExternalLocation
from inline_snapshot._external._format._protocol import get_format_handler
from inline_snapshot._external._format._protocol import get_format_handler_from_suffix
from inline_snapshot._global_state import state
from inline_snapshot._partial_call import partial_call
from inline_snapshot._partial_call import partial_check_args
from inline_snapshot._sentinels import undefined
from inline_snapshot._unmanaged import is_dirty_equal
from inline_snapshot._unmanaged import is_unmanaged
from inline_snapshot._utils import clone
from inline_snapshot._utils import triple_quote
from inline_snapshot.plugin._context_value import ContextValue

from ._custom import Custom
from ._custom import CustomizeHandler


@dataclass(frozen=True)
class CustomDefault(Custom):
    value: Custom = field(compare=False)

    def repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        yield from ()  # pragma: no cover
        # this should never be called because default values are never converted into code
        assert False

    def map(self, f):
        return self.value.map(f)

    def _needed_imports(self):
        yield from self.value._needed_imports()


@dataclass()
class CustomUnmanaged(Custom):
    value: Any

    def repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        yield from ()  # pragma: no cover
        return "'unmanaged'"

    def map(self, f):
        return f(self.value)


class CustomUndefined(Custom):
    def __init__(self):
        self.value = undefined

    def repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        yield from ()
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

    def repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        args = []
        for a in self.args:
            v = yield from a.repr(context)
            args.append(v)

        for k, v in self.kwargs.items():
            if not isinstance(v, CustomDefault):
                value = yield from v.repr(context)
                args.append(f"{k}={value}")

        return f"{yield from self._function.repr(context)}({', '.join(args)})"

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

    def repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        values = []
        for v in self.value:
            value = yield from v.repr(context)
            values.append(value)

        trailing_comma = self.trailing_comma and len(self.value) == 1
        return f"{self.braces[0]}{', '.join(values)}{', ' if trailing_comma else ''}{self.braces[1]}"

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

    def repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        values = []
        for k, v in self.value.items():
            key = yield from k.repr(context)
            value = yield from v.repr(context)
            values.append(f"{key}: {value}")

        return f"{{{ ', '.join(values)}}}"

    def _needed_imports(self):
        for k, v in self.value.items():
            yield from k._needed_imports()
            yield from v._needed_imports()


@dataclass(frozen=True)
class CustomExternal(Custom):
    value: Any
    format: str | None = None
    storage: str | None = None

    def map(self, f):
        return f(self.value)

    def repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        storage_name = self.storage or state().config.default_storage

        format = get_format_handler(self.value, self.format or "")

        location = ExternalLocation(
            storage=storage_name,
            stem="",
            suffix=self.format or format.suffix,
            filename=Path(context.file.filename),
            qualname=context.qualname,
        )

        tmp_file = state().new_tmp_path(location.suffix)

        storage = state().all_storages[storage_name]

        format.encode(self.value, tmp_file)
        location = storage.new_location(location, tmp_file)

        yield ExternalChange(
            "create",
            tmp_file,
            ExternalLocation.from_name("", context=context),
            location,
            format,
        )

        return f"external({location.to_str()!r})"

    def _needed_imports(self):
        return [("inline_snapshot", ["external"])]


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

    def repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        yield from ()
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


@dataclass
class Builder:
    _snapshot_context: AdapterContext
    _build_new_value: bool = False

    def _get_handler(self, v) -> Custom:

        from inline_snapshot._global_state import state

        if (
            self._snapshot_context is not None
            and (frame := self._snapshot_context.frame) is not None
        ):
            local_vars = [
                ContextValue(var_name, var_value)
                for var_name, var_value in frame.locals.items()
                if "@" not in var_name
            ]
            global_vars = [
                ContextValue(var_name, var_value)
                for var_name, var_value in frame.globals.items()
                if "@" not in var_name
            ]
        else:
            local_vars = []
            global_vars = []

        result = v

        while not isinstance(result, Custom):
            with compare_context():
                r = state().pm.hook.customize(
                    value=result,
                    builder=self,
                    local_vars=local_vars,
                    global_vars=global_vars,
                )
            if r is None:
                result = CustomValue(result)
            else:
                result = r

        result.__dict__["original_value"] = v
        return result

    def create_external(self, value: Any, format: str | None, storage: str | None):

        return CustomExternal(value, format=format, storage=storage)

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
