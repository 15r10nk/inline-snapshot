from __future__ import annotations

import ast
import warnings

from .._change import Delete
from .._change import DictInsert
from ..syntax_warnings import InlineSnapshotSyntaxWarning
from .adapter import Adapter
from .adapter import Item
from .adapter import adapter_map


class DictAdapter(Adapter):

    @classmethod
    def repr(cls, value):
        result = (
            "{"
            + ", ".join(f"{repr(k)}: {repr(value)}" for k, value in value.items())
            + "}"
        )

        if type(value) is not dict:
            result = f"{repr(type(value))}({result})"

        return result

    @classmethod
    def map(cls, value, map_function):
        return {k: adapter_map(v, map_function) for k, v in value.items()}

    @classmethod
    def items(cls, value, node):
        if node is None or not isinstance(node, ast.Dict):
            return [Item(value=value, node=None) for value in value.values()]

        result = []

        for value_key, node_key, node_value in zip(
            value.keys(), node.keys, node.values
        ):
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
            if not (
                isinstance(old_node, ast.Dict) and len(old_value) == len(old_node.keys)
            ):
                result = yield from self.value_assign(old_value, old_node, new_value)
                return result

            for key, value in zip(old_node.keys, old_node.values):
                if key is None:
                    warnings.warn_explicit(
                        "star-expressions are not supported inside snapshots",
                        filename=self.context.file._source.filename,
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
            if key not in new_value:
                # delete entries
                yield Delete("fix", self.context.file._source, node, old_value[key])

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
                result[key] = yield from self.get_adapter(
                    old_value[key], new_value[key]
                ).assign(old_value[key], node, new_value[key])

                if to_insert:
                    new_code = [
                        (
                            self.context.file._value_to_code(k),
                            self.context.file._value_to_code(v),
                        )
                        for k, v in to_insert
                    ]
                    yield DictInsert(
                        "fix",
                        self.context.file._source,
                        old_node,
                        insert_pos,
                        new_code,
                        to_insert,
                    )
                    to_insert = []

                insert_pos += 1

        if to_insert:
            new_code = [
                (
                    self.context.file._value_to_code(k),
                    self.context.file._value_to_code(v),
                )
                for k, v in to_insert
            ]
            yield DictInsert(
                "fix",
                self.context.file._source,
                old_node,
                len(old_value),
                new_code,
                to_insert,
            )

        return result
