import ast
from typing import Generator
from typing import Iterator
from typing import cast

from inline_snapshot._customize._custom_dict import CustomDict
from inline_snapshot._customize._custom_undefined import CustomUndefined

from ..._change import ChangeBase
from ..._change import Delete
from ..._change import DictInsert
from ..._global_state import state
from ..snapshot_data import SnapshotData
from ..snapshot_data import SnapshotOperation
from ..undecided_value import UndecidedValue


class DictOperation(SnapshotOperation):
    requested = "snapshot[key]"
    current = "snapshot[key]"

    def __init__(self):
        self.children: dict = {}

    def getitem(self, value, index):
        if isinstance(value._new_value, CustomUndefined):
            value._new_value = CustomDict({})

        index = value.to_custom(index)

        if index not in self.children:
            if isinstance(value._old_value, CustomUndefined):
                state().missing_values += 1
                old_value = {}
            else:
                old_value = value._old_value.value

            child_node = None
            if value._ast_node is not None:
                assert isinstance(value._ast_node, ast.Dict)
                old_keys = [k for k in old_value.keys()]
                if index in old_keys:
                    pos = old_keys.index(index)
                    child_node = value._ast_node.values[pos]

            self.children[index] = SnapshotData()
        else:
            if isinstance(value._old_value, CustomUndefined):
                old_value = {}
            else:
                old_value = value._old_value.value

            child_node = None
            if value._ast_node is not None and index in old_value:
                assert isinstance(value._ast_node, ast.Dict)
                old_keys = list(old_value)
                child_node = value._ast_node.values[old_keys.index(index)]

        return UndecidedValue(
            old_value.get(index, CustomUndefined()),
            child_node,
            value._context,
            self.children[index],
            on_change=lambda child, context: self._child_changed(
                value, index, child, context
            ),
            eager_changes=value._eager_changes,
        )

    def _child_changed(self, value, key, child: SnapshotData, context):
        value._context = context
        if not isinstance(child._new_value, CustomUndefined):
            value._new_value.value[key] = child._new_value
        value._refresh_changes()

    def _new_code(self, value) -> Generator[ChangeBase, None, str]:
        values = []
        for k, child in self.children.items():
            if child.rendered_new_code is not None:
                new_key = yield from k._code_repr(value._context)
                values.append(f"{new_key}: {child.rendered_new_code}")

        return "{" + ", ".join(values) + "}"

    def _get_changes(self, value) -> Iterator[ChangeBase]:

        assert not isinstance(value._old_value, CustomUndefined)

        if value._ast_node is None:
            values: list[ast.expr | None] = [None] * len(value._old_value.value)
        else:
            assert isinstance(value._ast_node, ast.Dict)
            values = cast(list[ast.expr | None], value._ast_node.values)

        for key, node in zip(value._old_value.value.keys(), values):
            if key in self.children:
                # check values with same keys
                yield from self.children[key].changes
            else:
                # delete entries
                yield Delete("trim", value._file, node)

        to_insert = []
        for key, child in self.children.items():
            if (
                key not in value._old_value.value
                and child.rendered_new_code is not None
            ):
                # add new values
                new_key = yield from key._code_repr(value._context)

                to_insert.append((new_key, child.rendered_new_code))

        if to_insert:
            yield DictInsert(
                "create",
                value._file,
                cast(ast.Dict, value._ast_node),
                len(value._old_value.value),
                to_insert,
            )
