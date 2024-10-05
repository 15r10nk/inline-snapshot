import ast
import typing
from dataclasses import is_dataclass


def get_adapter(value):
    if is_dataclass(value):
        return DataclassAdapter()

    if isinstance(value, list):
        return ListAdapter()

    if isinstance(value, tuple):
        return TupleAdapter()

    if isinstance(value, dict):
        return DictAdapter()


class Item(typing.NamedTuple):
    value: typing.Any
    node: ast.expr


class DataclassAdapter:

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


class ListAdapter:
    def items(self, value, node):

        assert isinstance(node, ast.List)
        assert len(value) == len(node.elts)

        return [Item(value=v, node=n) for v, n in zip(value, node.elts)]


class TupleAdapter:
    def items(self, value, node):

        assert isinstance(node, ast.Tuple)
        assert len(value) == len(node.elts)

        return [Item(value=v, node=n) for v, n in zip(value, node.elts)]


class DictAdapter:
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
