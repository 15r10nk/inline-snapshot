import ast
from typing import Iterator

from .._adapter.adapter import AdapterContext
from .._change import Change
from .._change import Delete
from .._change import DictInsert
from .._global_state import state
from .._inline_snapshot import UndecidedValue
from .._sentinels import undefined
from .generic_value import GenericValue


class DictValue(GenericValue):
    _current_op = "snapshot[key]"

    def __getitem__(self, index):

        if self._new_value is undefined:
            self._new_value = {}

        if index not in self._new_value:
            old_value = self._old_value
            if old_value is undefined:
                state().missing_values += 1
                old_value = {}

            child_node = None
            if self._ast_node is not None:
                assert isinstance(self._ast_node, ast.Dict)
                if index in old_value:
                    pos = list(old_value.keys()).index(index)
                    child_node = self._ast_node.values[pos]

            self._new_value[index] = UndecidedValue(
                old_value.get(index, undefined), child_node, self._context
            )

        return self._new_value[index]

    def _re_eval(self, value, context: AdapterContext):
        super()._re_eval(value, context)

        if self._new_value is not undefined and self._old_value is not undefined:
            for key, s in self._new_value.items():
                if key in self._old_value:
                    s._re_eval(self._old_value[key], context)

    def _new_code(self):
        return (
            "{"
            + ", ".join(
                [
                    f"{self._file._value_to_code(k)}: {v._new_code()}"
                    for k, v in self._new_value.items()
                    if not isinstance(v, UndecidedValue)
                ]
            )
            + "}"
        )

    def _get_changes(self) -> Iterator[Change]:

        assert self._old_value is not undefined

        if self._ast_node is None:
            values = [None] * len(self._old_value)
        else:
            assert isinstance(self._ast_node, ast.Dict)
            values = self._ast_node.values

        for key, node in zip(self._old_value.keys(), values):
            if key in self._new_value:
                # check values with same keys
                yield from self._new_value[key]._get_changes()
            else:
                # delete entries
                yield Delete("trim", self._file, node, self._old_value[key])

        to_insert = []
        for key, new_value_element in self._new_value.items():
            if key not in self._old_value and not isinstance(
                new_value_element, UndecidedValue
            ):
                # add new values
                to_insert.append((key, new_value_element._new_code()))

        if to_insert:
            new_code = [(self._file._value_to_code(k), v) for k, v in to_insert]
            yield DictInsert(
                "create",
                self._file,
                self._ast_node,
                len(self._old_value),
                new_code,
                to_insert,
            )
