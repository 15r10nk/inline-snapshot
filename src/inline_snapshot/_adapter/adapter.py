from __future__ import annotations

import ast
import typing
from dataclasses import is_dataclass

from inline_snapshot._source_file import SourceFile


def get_adapter_type(value):
    if is_dataclass(value):
        from .dataclass_adapter import DataclassAdapter

        return DataclassAdapter

    if isinstance(value, list):
        from .sequence_adapter import ListAdapter

        return ListAdapter

    if isinstance(value, tuple):
        from .sequence_adapter import TupleAdapter

        return TupleAdapter

    if isinstance(value, dict):
        from .dict_adapter import DictAdapter

        return DictAdapter

    from .value_adapter import ValueAdapter

    return ValueAdapter


class Item(typing.NamedTuple):
    value: typing.Any
    node: ast.expr


class Adapter:
    context: SourceFile

    def __init__(self, context):
        self.context = context

    def get_adapter(self, old_value, new_value) -> Adapter:
        # if type(old_value) is not type(new_value):
        #     from .value_adapter import ValueAdapter
        #     return ValueAdapter(self.context)

        adapter_type = get_adapter_type(old_value)
        if adapter_type is not None:
            return adapter_type(self.context)
        assert False

    def assign(self, old_value, old_node, new_value):
        raise NotImplementedError
