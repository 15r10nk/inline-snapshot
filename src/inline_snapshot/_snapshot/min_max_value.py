from typing import Generator
from typing import Iterator
from typing import List
from typing import Optional

from inline_snapshot._customize._custom_undefined import CustomUndefined
from inline_snapshot._customize._uncustomized import Uncustomized
from inline_snapshot._generator_utils import split_gen
from inline_snapshot._new_adapter import NewAdapter

from .._change import ChangeBase
from .._change import Replace
from .._global_state import state
from .generic_value import GenericValue
from .generic_value import ignore_old_value


class MinMaxValue(GenericValue):
    """Generic implementation for <=, >="""

    _changes: Optional[List[ChangeBase]]

    @staticmethod
    def cmp(a, b):
        raise NotImplementedError

    def _set_new_value(self, other):
        if (
            state().active
            and self._ast_node is not None
            and self._context.expr.node is not None
        ):
            result = split_gen(
                NewAdapter(self._context).compare(
                    self._old_value, self._ast_node, Uncustomized(other)
                )
            )
            self._new_value = result.value
            self._changes = result.list
        else:
            self._new_value = self.to_custom(
                other, self._old_value, _build_new_value=True
            )
            self._changes = None

    def _generic_cmp(self, other):
        if isinstance(self._old_value, CustomUndefined):
            state().missing_values += 1

        if isinstance(self._new_value, CustomUndefined):
            self._set_new_value(other)
            if isinstance(self._old_value, CustomUndefined) or ignore_old_value():
                return True
            return self._return(self.cmp(self._old_value._eval(), other))
        else:
            if not self.cmp(self._new_value._eval(), other):
                self._set_new_value(other)

        return self._return(self.cmp(self._visible_value()._eval(), other))

    def _new_code(self) -> Generator[ChangeBase, None, str]:
        code = yield from self._new_value._code_repr(self._context)
        return code

    def _get_changes(self) -> Iterator[ChangeBase]:
        if getattr(self, "_changes", None) is not None:
            old_eval = self._old_value._eval()
            new_eval = self._new_value._eval()
            for change in self._changes:
                if (
                    change.flag == "fix"
                    and self.cmp(old_eval, new_eval)
                    and not self.cmp(new_eval, old_eval)
                ):
                    change.flag = "trim"
                yield change
            return

        new_code = yield from self._new_code()

        if not self.cmp(self._old_value._eval(), self._new_value._eval()):
            flag = "fix"
        elif not self.cmp(self._new_value._eval(), self._old_value._eval()):
            flag = "trim"
        elif self._file.code_changed(self._ast_node, new_code):
            flag = "update"
        else:
            return

        yield Replace(
            node=self._ast_node,
            file=self._file,
            new_code=new_code,
            flag=flag,
        )


class MinValue(MinMaxValue):
    """
    handles:

    >>> snapshot(5) <= 6
    True

    >>> 6 >= snapshot(5)
    True

    """

    _current_op = "x >= snapshot"

    @staticmethod
    def cmp(a, b):
        return a <= b

    __le__ = MinMaxValue._generic_cmp


class MaxValue(MinMaxValue):
    """
    handles:

    >>> snapshot(5) >= 4
    True

    >>> 4 <= snapshot(5)
    True

    """

    _current_op = "x <= snapshot"

    @staticmethod
    def cmp(a, b):
        return a >= b

    __ge__ = MinMaxValue._generic_cmp
