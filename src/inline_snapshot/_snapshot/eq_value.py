from typing import Generator
from typing import Iterator
from typing import List

from inline_snapshot._customize._custom_undefined import CustomUndefined
from inline_snapshot._customize._uncustomized import Uncustomized
from inline_snapshot._generator_utils import split_gen
from inline_snapshot._new_adapter import NewAdapter

from .._change import CategoryChange
from .._change import Change
from .._change import ChangeBase
from .._compare_context import compare_only
from .._global_state import state
from .generic_value import GenericValue


class EqValue(GenericValue):
    _current_op = "x == snapshot"
    _changes: List[Change]

    def __eq__(self, other):
        if isinstance(self._old_value, CustomUndefined):
            state().missing_values += 1

        if not compare_only() and isinstance(self._new_value, CustomUndefined):
            self._changes = []

            if not state().active:
                return self._return(self._old_value._eval() == other)

            if self._ast_node is not None:
                result = split_gen(
                    NewAdapter(self._context).compare(
                        self._old_value, self._ast_node, Uncustomized(other)
                    )
                )
                self._changes = result.list
                self._new_value = result.value
            else:
                self._new_value = self.to_custom(other, _build_new_value=True)
                if isinstance(self._old_value, CustomUndefined):
                    self._changes.append(CategoryChange("create"))
                elif self._old_value._eval() != other:
                    self._changes.append(CategoryChange("fix"))

        return self._return(
            self._old_value._eval() == other,
            self._new_value._eval() == other,
        )

    def _new_code(self) -> Generator[ChangeBase, None, str]:
        code = yield from self._new_value._code_repr(self._context)
        return code

    def _get_changes(self) -> Iterator[Change]:
        return iter(getattr(self, "_changes", []))
