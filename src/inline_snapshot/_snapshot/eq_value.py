from typing import Generator
from typing import Iterator
from typing import List

from inline_snapshot._code_repr import mock_repr
from inline_snapshot._customize import CustomUndefined
from inline_snapshot._generator_utils import split_gen
from inline_snapshot._new_adapter import NewAdapter

from .._change import Change
from .._change import ChangeBase
from .._compare_context import compare_only
from .._global_state import state
from .generic_value import GenericValue


class EqValue(GenericValue):
    _current_op = "x == snapshot"
    _changes: List[Change]

    def __eq__(self, other):
        with mock_repr(self._context):
            custom_other = self.get_builder(_build_new_value=True)._get_handler(other)

        if isinstance(self._old_value, CustomUndefined):
            state().missing_values += 1

        if not compare_only() and isinstance(self._new_value, CustomUndefined):
            self._changes = []

            adapter = NewAdapter(self._context)

            result = split_gen(
                adapter.compare(self._old_value, self._ast_node, custom_other)
            )
            self._changes = result.list
            self._new_value = result.value

        return self._return(
            self._old_value.eval() == other,
            self._new_value.eval() == other,
        )

    def _new_code(self) -> Generator[ChangeBase, None, str]:
        code = yield from self._new_value.repr(self._context)
        return code

    def _get_changes(self) -> Iterator[Change]:
        return iter(getattr(self, "_changes", []))
