from __future__ import annotations

import ast
import warnings
from collections import defaultdict

from .._align import add_x
from .._align import align
from .._change import Delete
from .._change import ListInsert
from .._compare_context import compare_context
from ..syntax_warnings import InlineSnapshotSyntaxWarning
from .adapter import Adapter
from .adapter import adapter_map
from .adapter import Item


class SequenceAdapter(Adapter):
    node_type: type
    value_type: type
    braces: str
    trailing_comma: bool

    @classmethod
    def repr(cls, value):
        if len(value) == 1 and cls.trailing_comma:
            seq = repr(value[0]) + ","
        else:
            seq = ", ".join(map(repr, value))
        return cls.braces[0] + seq + cls.braces[1]

    @classmethod
    def map(cls, value, map_function):
        result = [adapter_map(v, map_function) for v in value]
        return cls.value_type(result)

    def items(self, value, node):
        if node is None:
            return [Item(value=v, node=None) for v in value]

        assert isinstance(node, self.node_type), (node, self)
        assert len(value) == len(node.elts)

        return [Item(value=v, node=n) for v, n in zip(value, node.elts)]

    def assign(self, old_value, old_node, new_value):
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

        with compare_context():
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
                v = yield from self.get_adapter(
                    old_value_element, new_value_element
                ).assign(old_value_element, old_node_element, new_value_element)
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
    braces = "[]"
    trailing_comma = False


class TupleAdapter(SequenceAdapter):
    node_type = ast.Tuple
    value_type = tuple
    braces = "()"
    trailing_comma = True
