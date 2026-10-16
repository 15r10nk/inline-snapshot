from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Generator
from typing import Iterator

from inline_snapshot._customize._custom_undefined import CustomUndefined
from inline_snapshot._generator_utils import split_gen
from inline_snapshot._new_adapter import NewAdapter

from ..._change import ChangeBase
from ..._change import Replace
from ..._global_state import state
from ..snapshot_value import ignore_old_value
from .base import SnapshotOperation

if TYPE_CHECKING:
    from ..snapshot_value import SnapshotValue


class MinMaxOperation(SnapshotOperation):
    """Generic implementation for <=, >="""

    _changes: list[ChangeBase] | None

    @staticmethod
    def cmp(a: Any, b: Any) -> bool:
        raise NotImplementedError

    def __init__(self) -> None:
        self.changes: list[ChangeBase] | None = None

    def _set_new_value(self, value: SnapshotValue, other: Any) -> None:
        if (
            state().active
            and value._ast_node is not None
            and value._context.expr.node is not None
        ):
            result = split_gen(
                NewAdapter(value._context).compare(
                    value._old_value, value._ast_node, other
                )
            )
            value._new_value = result.value
            self.changes = result.list
        else:
            value._new_value = value.to_custom(other, _build_new_value=True)
            self.changes = None

    def compare(self, value: SnapshotValue, other: Any) -> bool:
        if isinstance(value._old_value, CustomUndefined):
            state().missing_values += 1

        if isinstance(value._new_value, CustomUndefined):
            self._set_new_value(value, other)
            if isinstance(value._old_value, CustomUndefined) or ignore_old_value():
                value._refresh_changes()
                return True
            result = value._return(self.cmp(value._old_value._eval(), other))
        else:
            if not self.cmp(value._new_value._eval(), other):
                self._set_new_value(value, other)
            result = value._return(self.cmp(value._visible_value()._eval(), other))

        value._refresh_changes()
        return result

    def new_code(self, value: SnapshotValue) -> Generator[ChangeBase, None, str]:
        code = yield from value._new_value._code_repr(value._context)
        return code

    def get_changes(self, value: SnapshotValue) -> Iterator[ChangeBase]:
        changes = self.changes
        if changes is not None:
            old_eval = value._old_value._eval()
            new_eval = value._new_value._eval()
            for change in changes:
                if (
                    change.flag == "fix"
                    and self.cmp(old_eval, new_eval)
                    and not self.cmp(new_eval, old_eval)
                ):
                    change.flag = "trim"
                yield change
            return

        new_code = yield from self.new_code(value)

        if not self.cmp(value._old_value._eval(), value._new_value._eval()):
            flag = "fix"
        elif not self.cmp(value._new_value._eval(), value._old_value._eval()):
            flag = "trim"
        elif value._file.code_changed(value._ast_node, new_code):
            flag = "update"
        else:
            return

        yield Replace(
            node=value._ast_node,  # type: ignore[arg-type]
            file=value._file,
            new_code=new_code,
            flag=flag,
        )


class MinOperation(MinMaxOperation):
    """
    handles:

    >>> snapshot(5) <= 6
    True

    >>> 6 >= snapshot(5)
    True

    """

    requested = "<="
    current = "x >= snapshot"

    @staticmethod
    def cmp(a: Any, b: Any) -> bool:
        return a <= b


class MaxOperation(MinMaxOperation):
    """
    handles:

    >>> snapshot(5) >= 4
    True

    >>> 4 <= snapshot(5)
    True

    """

    requested = ">="
    current = "x <= snapshot"

    @staticmethod
    def cmp(a: Any, b: Any) -> bool:
        return a >= b
