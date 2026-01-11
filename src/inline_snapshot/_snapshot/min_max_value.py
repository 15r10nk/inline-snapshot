from typing import Generator
from typing import Iterator

from inline_snapshot._customize._custom_undefined import CustomUndefined

from .._change import ChangeBase
from .._change import Replace
from .._global_state import state
from .generic_value import GenericValue
from .generic_value import ignore_old_value


class MinMaxValue(GenericValue):
    """Generic implementation for <=, >="""

    @staticmethod
    def cmp(a, b):
        raise NotImplementedError

    def _generic_cmp(self, other):
        if isinstance(self._old_value, CustomUndefined):
            state().missing_values += 1

        if isinstance(self._new_value, CustomUndefined):
            self._new_value = self.to_custom(other)
            if isinstance(self._old_value, CustomUndefined) or ignore_old_value():
                return True
            return self._return(self.cmp(self._old_value._eval(), other))
        else:
            if not self.cmp(self._new_value._eval(), other):
                self._new_value = self.to_custom(other)

        return self._return(self.cmp(self._visible_value()._eval(), other))

    def _new_code(self) -> Generator[ChangeBase, None, str]:
        code = yield from self._new_value._code_repr(self._context)
        return code

    def _get_changes(self) -> Iterator[ChangeBase]:
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
            old_value=self._old_value._eval(),
            new_value=self._new_value._eval(),
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
