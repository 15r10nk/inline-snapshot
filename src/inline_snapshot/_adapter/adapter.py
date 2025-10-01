from __future__ import annotations

import ast
import typing
from dataclasses import dataclass

import pytest

from inline_snapshot._customize import CustomCall
from inline_snapshot._customize import CustomDict
from inline_snapshot._customize import CustomList
from inline_snapshot._customize import CustomTuple
from inline_snapshot._customize import CustomUndefined
from inline_snapshot._customize import CustomValue
from inline_snapshot._source_file import SourceFile


def get_adapter_type(value):

    if isinstance(value, CustomCall):
        from .generic_call_adapter import CallAdapter

        pytest.skip()

        return CallAdapter

    if isinstance(value, CustomList):
        from .sequence_adapter import ListAdapter

        pytest.skip()

        return ListAdapter

    if isinstance(value, CustomTuple):
        from .sequence_adapter import TupleAdapter

        pytest.skip()

        return TupleAdapter

    if isinstance(value, CustomDict):
        from .dict_adapter import DictAdapter

        pytest.skip()

        return DictAdapter

    if isinstance(value, (CustomValue, CustomUndefined)):
        from .value_adapter import ValueAdapter

        return ValueAdapter

    raise AssertionError(f"no handler for {type(value)}")


class Item(typing.NamedTuple):
    value: typing.Any
    node: ast.expr


@dataclass
class FrameContext:
    globals: dict
    locals: dict


@dataclass
class AdapterContext:
    file: SourceFile
    frame: FrameContext | None
    qualname: str

    def eval(self, node):
        assert self.frame is not None

        return eval(
            compile(ast.Expression(node), self.file.filename, "eval"),
            self.frame.globals,
            self.frame.locals,
        )


class Adapter:
    context: AdapterContext

    def __init__(self, context: AdapterContext):
        self.context = context

    def get_adapter(self, old_value, new_value) -> Adapter:
        if type(old_value) is not type(new_value):
            from .value_adapter import ValueAdapter

            return ValueAdapter(self.context)

        adapter_type = get_adapter_type(old_value)
        if adapter_type is not None:
            return adapter_type(self.context)
        assert False

    def assign(self, old_value, old_node, new_value):
        raise NotImplementedError(self)

    def value_assign(self, old_value, old_node, new_value):
        from .value_adapter import ValueAdapter

        adapter = ValueAdapter(self.context)
        result = yield from adapter.assign(old_value, old_node, new_value)
        return result

    @classmethod
    def map(cls, value, map_function):
        raise NotImplementedError(cls)

    @classmethod
    def repr(cls, value):
        raise NotImplementedError(cls)


def adapter_map(value, map_function):
    return get_adapter_type(value).map(value, map_function)
