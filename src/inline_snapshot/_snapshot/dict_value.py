import ast
from typing import Generator
from typing import Iterator

from inline_snapshot._customize._custom_dict import CustomDict
from inline_snapshot._customize._custom_undefined import CustomUndefined

from .._change import ChangeBase
from .._change import Delete
from .._change import DictInsert
from .._global_state import state
from .generic_value import GenericValue
from .snapshot_data import SnapshotData
from .undecided_value import UndecidedValue


class DictValue(GenericValue):
    _current_op = "snapshot[key]"

    _new_value: CustomDict
    _old_value: CustomDict
    _ast_node: ast.Dict

    def __getitem__(self, index):
        if isinstance(self._new_value, CustomUndefined):
            self._new_value = CustomDict({})

        index = self.to_custom(index)

        if index not in self._data.children:
            if isinstance(self._old_value, CustomUndefined):
                state().missing_values += 1
                old_value = {}
            else:
                old_value = self._old_value.value

            child_node = None
            if self._ast_node is not None:
                assert isinstance(self._ast_node, ast.Dict)
                old_keys = [k for k in old_value.keys()]
                if index in old_keys:
                    pos = old_keys.index(index)
                    child_node = self._ast_node.values[pos]

            self._data.children[index] = SnapshotData()
        else:
            if isinstance(self._old_value, CustomUndefined):
                old_value = {}
            else:
                old_value = self._old_value.value

            child_node = None
            if self._ast_node is not None and index in old_value:
                assert isinstance(self._ast_node, ast.Dict)
                old_keys = list(old_value)
                child_node = self._ast_node.values[old_keys.index(index)]

        return UndecidedValue(
            old_value.get(index, CustomUndefined()),
            child_node,
            self._context,
            self._data.children[index],
            parent=self,
            parent_key=index,
            eager_changes=self._eager_changes,
        )

    def _child_changed(self, key, child: SnapshotData, context):
        self._context = context
        if not isinstance(child._new_value, CustomUndefined):
            self._new_value.value[key] = child._new_value
        self._refresh_changes()

    def _new_code(self) -> Generator[ChangeBase, None, str]:
        values = []
        for k, child in self._data.children.items():
            if child.rendered_new_code is not None:
                new_key = yield from k._code_repr(self._context)
                values.append(f"{new_key}: {child.rendered_new_code}")

        return "{" + ", ".join(values) + "}"

    def _get_changes(self) -> Iterator[ChangeBase]:

        assert not isinstance(self._old_value, CustomUndefined)

        if self._ast_node is None:
            values = [None] * len(self._old_value.value)
        else:
            assert isinstance(self._ast_node, ast.Dict)
            values = self._ast_node.values

        for key, node in zip(self._old_value.value.keys(), values):
            if key in self._data.children:
                # check values with same keys
                yield from self._data.children[key].changes
            else:
                # delete entries
                yield Delete("trim", self._file, node)

        to_insert = []
        for key, child in self._data.children.items():
            if key not in self._old_value.value and child.rendered_new_code is not None:
                # add new values
                new_key = yield from key._code_repr(self._context)

                to_insert.append((new_key, child.rendered_new_code))

        if to_insert:
            yield DictInsert(
                "create",
                self._file,
                self._ast_node,
                len(self._old_value.value),
                to_insert,
            )
