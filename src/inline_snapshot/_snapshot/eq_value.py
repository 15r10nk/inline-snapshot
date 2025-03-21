from typing import Iterator
from typing import List

from inline_snapshot._adapter.adapter import Adapter

from .._change import Change
from .._compare_context import compare_only
from .._global_state import state
from .._sentinels import undefined
from .generic_value import GenericValue
from .generic_value import clone


class EqValue(GenericValue):
    _current_op = "x == snapshot"
    _changes: List[Change]

    def __eq__(self, other):
        if self._old_value is undefined:
            state().missing_values += 1

        if not compare_only() and self._new_value is undefined:
            self._changes = []
            adapter = Adapter(self._context).get_adapter(self._old_value, other)
            it = iter(adapter.assign(self._old_value, self._ast_node, clone(other)))
            while True:
                try:
                    self._changes.append(next(it))
                except StopIteration as ex:
                    self._new_value = ex.value
                    break

        return self._return(self._old_value == other, self._new_value == other)

    def _new_code(self):
        return self._file._value_to_code(self._new_value)

    def _get_changes(self) -> Iterator[Change]:
        return iter(self._changes)
