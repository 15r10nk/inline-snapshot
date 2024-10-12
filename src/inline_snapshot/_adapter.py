from __future__ import annotations

import ast
import typing
import warnings
from collections import defaultdict
from dataclasses import is_dataclass

from inline_snapshot._context import Context
from inline_snapshot._update_allowed import update_allowed
from inline_snapshot._utils import value_to_token

from ._align import add_x
from ._align import align
from ._change import Delete
from ._change import DictInsert
from ._change import ListInsert
from ._change import Replace


def get_adapter_type(value):
    if is_dataclass(value):
        return DataclassAdapter

    if isinstance(value, list):
        return ListAdapter

    if isinstance(value, tuple):
        return TupleAdapter

    if isinstance(value, dict):
        return DictAdapter

    return ValueAdapter


class Item(typing.NamedTuple):
    value: typing.Any
    node: ast.expr


class Adapter:
    context: Context

    def __init__(self, context):
        self.context = context

    def get_adapter(self, value) -> Adapter:
        adapter_type = get_adapter_type(value)
        if adapter_type is not None:
            return adapter_type(self.context)

        assert False

    def assign(self, old_value, old_node, new_value):
        raise NotImplementedError


class ValueAdapter(Adapter):

    def assign(self, old_value, old_node, new_value):
        # generic fallback

        # because IsStr() != IsStr()
        if type(old_value) is type(new_value) and not update_allowed(new_value):
            return old_value

        if old_node is None:
            new_token = []
        else:
            new_token = value_to_token(new_value)

        if not old_value == new_value:
            flag = "fix"
        elif (
            old_node is not None
            and update_allowed(old_value)
            and self.context._token_of_node(old_node) != new_token
        ):
            flag = "update"
        else:
            # equal and equal repr
            return old_value

        new_code = self.context._token_to_code(new_token)

        yield Replace(
            node=old_node,
            source=self.context._source,
            new_code=new_code,
            flag=flag,
            old_value=old_value,
            new_value=new_value,
        )

        return new_value


class DataclassAdapter(Adapter):

    def items(self, value, node):

        assert isinstance(node, ast.Call)
        assert len(value) == len(node.keywords)
        assert not node.args
        assert all(kw.arg for kw in node.keywords)

        return [
            Item(value=getattr(value, kw.arg), node=kw.value)
            for kw in node.keywords
            if kw.arg
        ]

    def assign(self, old_value, old_node, new_value):
        return old_value
        yield


class InlineSnapshotSyntaxWarning(Warning):
    pass


class SequenceAdapter(Adapter):
    node_type: type
    value_type: type

    def items(self, value, node):

        assert isinstance(node, self.node_type), (node, self)
        assert len(value) == len(node.elts)

        return [Item(value=v, node=n) for v, n in zip(value, node.elts)]

    def assign(self, old_value, old_node, new_value):
        if isinstance(new_value, self.value_type) and isinstance(
            old_value, self.value_type
        ):

            if old_node is not None:
                assert isinstance(
                    old_node, ast.List if isinstance(old_value, list) else ast.Tuple
                )

                for e in old_node.elts:
                    if isinstance(e, ast.Starred):
                        warnings.warn_explicit(
                            "star-expressions are not supported inside snapshots",
                            filename=self.context.filename,
                            lineno=e.lineno,
                            category=InlineSnapshotSyntaxWarning,
                        )
                        return old_value

            diff = add_x(align(old_value, new_value))
            old = zip(
                old_value,
                old_node.elts if old_node is not None else [None] * len(old_value),
            )
            new = iter(new_value)
            old_position = 0
            to_insert = defaultdict(list)
            result = []
            for c in diff:
                if c in "mx":
                    old_value_element, old_node_element = next(old)
                    new_value_element = next(new)
                    v = yield from self.get_adapter(old_value_element).assign(
                        old_value_element, old_node_element, new_value_element
                    )
                    result.append(v)
                    old_position += 1
                elif c == "i":
                    new_value_element = next(new)
                    new_code = self.context._value_to_code(new_value_element)
                    result.append(new_value_element)
                    to_insert[old_position].append((new_code, new_value_element))
                elif c == "d":
                    old_value_element, old_node_element = next(old)
                    yield Delete(
                        "fix", self.context._source, old_node_element, old_value_element
                    )
                    old_position += 1
                else:
                    assert False

            for position, code_values in to_insert.items():
                yield ListInsert(
                    "fix", self.context._source, old_node, position, *zip(*code_values)
                )

            return self.value_type(result)


class ListAdapter(SequenceAdapter):
    node_type = ast.List
    value_type = list


class TupleAdapter(SequenceAdapter):
    node_type = ast.Tuple
    value_type = tuple


class DictAdapter(Adapter):
    def items(self, value, node):
        assert isinstance(node, ast.Dict)

        result = []

        for value_key, node_key, node_value in zip(
            value.keys(), node.keys, node.values
        ):
            if node_key is not None:
                try:
                    # this is just a sanity check, dicts should be ordered
                    node_key = ast.literal_eval(node_key)
                except Exception:
                    pass
                else:
                    assert node_key == value_key

            result.append(Item(value=value[value_key], node=node_value))

        return result

    def assign(self, old_value, old_node, new_value):
        if old_node is not None:
            assert isinstance(old_node, ast.Dict)
            assert len(old_value) == len(old_node.keys)

            for key, value in zip(old_node.keys, old_node.values):
                if key is None:
                    warnings.warn_explicit(
                        "star-expressions are not supported inside snapshots",
                        filename=self.context._source.filename,
                        lineno=value.lineno,
                        category=InlineSnapshotSyntaxWarning,
                    )
                    return old_value

            for value, node in zip(old_value.keys(), old_node.keys):

                try:
                    # this is just a sanity check, dicts should be ordered
                    node_value = ast.literal_eval(node)
                except:
                    continue
                assert node_value == value

        result = {}
        for key, node in zip(
            old_value.keys(),
            (old_node.values if old_node is not None else [None] * len(old_value)),
        ):
            if not key in new_value:
                # delete entries
                yield Delete("fix", self.context._source, node, old_value[key])

        to_insert = []
        insert_pos = 0
        for key, new_value_element in new_value.items():
            if key not in old_value:
                # add new values
                to_insert.append((key, new_value_element))
                result[key] = new_value_element
            else:
                if isinstance(old_node, ast.Dict):
                    node = old_node.values[list(old_value.keys()).index(key)]
                else:
                    node = None
                # check values with same keys
                result[key] = yield from self.get_adapter(old_value[key]).assign(
                    old_value[key], node, new_value[key]
                )

                if to_insert:
                    new_code = [
                        (self.context._value_to_code(k), self.context._value_to_code(v))
                        for k, v in to_insert
                    ]
                    yield DictInsert(
                        "fix",
                        self.context._source,
                        old_node,
                        insert_pos,
                        new_code,
                        to_insert,
                    )
                    to_insert = []

                insert_pos += 1

        if to_insert:
            new_code = [
                (self.context._value_to_code(k), self.context._value_to_code(v))
                for k, v in to_insert
            ]
            yield DictInsert(
                "fix",
                self.context._source,
                old_node,
                len(old_value),
                new_code,
                to_insert,
            )

        return result
