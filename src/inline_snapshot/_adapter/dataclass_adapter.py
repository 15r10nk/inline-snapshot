from __future__ import annotations

import ast
import warnings
from dataclasses import fields
from dataclasses import MISSING

from inline_snapshot._adapter.value_adapter import ValueAdapter

from .._change import CallArg
from .._change import Delete
from ..syntax_warnings import InlineSnapshotSyntaxWarning
from .adapter import Adapter
from .adapter import Item


class DataclassAdapter(Adapter):

    def items(self, value, node):

        assert isinstance(node, ast.Call)
        assert len(value) == len(node.keywords)
        assert not node.args
        assert all(kw.arg for kw in node.keywords)

        return [
            Item(value=self.argument(value, kw.arg), node=kw.value)
            for kw in node.keywords
            if kw.arg
        ]

    def arguments(self, value):

        kwargs = {}

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

                kwargs[field.name] = field_value

        return ([], kwargs)

    def argument(self, value, pos_or_name):
        assert isinstance(pos_or_name, str)
        return getattr(value, pos_or_name)

    def assign(self, old_value, old_node, new_value):
        if old_node is None:

            value = yield from ValueAdapter(self.context).assign(
                old_value, old_node, new_value
            )
            return value

        assert isinstance(old_node, ast.Call)

        for kw in old_node.keywords:
            if kw.arg is None:
                warnings.warn_explicit(
                    "star-expressions are not supported inside snapshots",
                    filename=self.context._source.filename,
                    lineno=kw.lineno,
                    category=InlineSnapshotSyntaxWarning,
                )
                return old_value

        new_args, new_kwargs = self.arguments(new_value)

        result_kwargs = {}
        for kw in old_node.keywords:
            if not kw.arg in new_kwargs:
                # delete entries
                yield Delete(
                    "fix",
                    self.context._source,
                    kw.value,
                    self.argument(old_value, kw.arg),
                )

        old_node_kwargs = {kw.arg: kw.value for kw in old_node.keywords}

        to_insert = []
        insert_pos = 0
        for key, new_value_element in new_kwargs.items():
            if key not in old_node_kwargs:
                # add new values
                to_insert.append((key, new_value_element))
                result_kwargs[key] = new_value_element
            else:
                node = old_node_kwargs[key]

                # check values with same keys
                old_value_element = self.argument(old_value, key)
                result_kwargs[key] = yield from self.get_adapter(
                    old_value_element
                ).assign(old_value_element, node, new_value_element)

                if to_insert:
                    for key, value in to_insert:

                        yield CallArg(
                            flag="fix",
                            file=self.context._source,
                            node=old_node,
                            arg_pos=insert_pos,
                            arg_name=key,
                            new_code=f"{key} = {self.context._value_to_code(value)}",
                            new_value=(key, value),
                        )
                    to_insert = []

                insert_pos += 1

        if to_insert:

            for key, value in to_insert:

                yield CallArg(
                    flag="fix",
                    file=self.context._source,
                    node=old_node,
                    arg_pos=insert_pos,
                    arg_name=key,
                    new_code=f"{key} = {self.context._value_to_code(value)}",
                    new_value=(key, value),
                )

        return type(old_value)(**result_kwargs)
