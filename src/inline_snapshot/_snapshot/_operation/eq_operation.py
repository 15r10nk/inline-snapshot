from typing import Generator
from typing import Iterator
from typing import List

from inline_snapshot._customize._custom_undefined import CustomUndefined
from inline_snapshot._generator_utils import split_gen
from inline_snapshot._new_adapter import NewAdapter

from ..._change import CategoryChange
from ..._change import Change
from ..._change import ChangeBase
from ..._compare_context import compare_only
from ..._global_state import state
from ..snapshot_data import SnapshotOperation


class EqOperation(SnapshotOperation):
    requested = "=="
    current = "x == snapshot"

    def __init__(self):
        self.changes: List[Change] = []

    def compare(self, value, other):
        changed = False
        if isinstance(value._old_value, CustomUndefined):
            state().missing_values += 1

        is_equal = value._old_value._eval() == other

        if isinstance(value._new_value, CustomUndefined):
            if not compare_only():
                changed = True
                self.changes = []

                if not state().active:
                    return value._return(value._old_value._eval() == other)

                if not state().config.show_updates and not state().update_flags.update:
                    if is_equal:
                        value._new_value = value._old_value
                        value._refresh_changes()
                        return True

                if value._ast_node is not None:
                    result = split_gen(
                        NewAdapter(value._context).compare(
                            value._old_value, value._ast_node, other
                        )
                    )
                    self.changes = result.list
                    value._new_value = result.value
                else:
                    # No argument node: do not use the adapter (it requires a node)
                    # and do not rewrite source. Report flags only.
                    if isinstance(value._old_value, CustomUndefined):
                        self.changes.append(CategoryChange("create"))
                        value._new_value = value.to_custom(other, _build_new_value=True)
                    elif value._old_value._eval() != other:
                        self.changes.append(CategoryChange("fix"))
                        if value._context.expr.node is not None:
                            value._new_value = value.to_custom(
                                other, _build_new_value=True
                            )
                    else:
                        value._new_value = value._old_value

        result = value._return(
            is_equal,
            value._new_value._eval() == other,
        )
        if changed:
            value._refresh_changes()
        return result

    def _new_code(self, value) -> Generator[ChangeBase, None, str]:
        code = yield from value._new_value._code_repr(value._context)
        return code

    def _get_changes(self, value) -> Iterator[Change]:
        return iter(self.changes)
