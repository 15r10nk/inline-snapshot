from typing import Iterator
from typing import List

from inline_snapshot._customize import Builder
from inline_snapshot._customize import CustomUndefined
from inline_snapshot._new_adapter import NewAdapter
from inline_snapshot._utils import map_strings

from .._change import Change
from .._compare_context import compare_only
from .._global_state import state
from .generic_value import GenericValue


class EqValue(GenericValue):
    _current_op = "x == snapshot"
    _changes: List[Change]

    def __eq__(self, other):
        custom_other = Builder(_build_new_value=True)._get_handler(other)

        if isinstance(self._old_value, CustomUndefined):
            state().missing_values += 1

        if not compare_only() and isinstance(self._new_value, CustomUndefined):
            self._changes = []

            adapter = NewAdapter(self._context)
            it = iter(adapter.compare(self._old_value, self._ast_node, custom_other))
            while True:
                try:
                    self._changes.append(next(it))
                except StopIteration as ex:
                    self._new_value = ex.value
                    break

        return self._return(
            self._old_value.eval() == other,
            self._new_value.eval() == other,
        )

    def _new_code(self):
        return self._file._token_to_code(map_strings(self._new_value.repr()))

    def _get_changes(self) -> Iterator[Change]:
        return iter(getattr(self, "_changes", []))
