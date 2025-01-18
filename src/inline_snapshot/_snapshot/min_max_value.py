from typing import Iterator

from .._change import Change
from .._change import Replace
from .._global_state import state
from .._sentinels import undefined
from .._utils import value_to_token
from .generic_value import GenericValue
from .generic_value import clone
from .generic_value import ignore_old_value


class MinMaxValue(GenericValue):
    """Generic implementation for <=, >="""

    @staticmethod
    def cmp(a, b):
        raise NotImplementedError

    def _generic_cmp(self, other):
        if self._old_value is undefined:
            state().missing_values += 1

        if self._new_value is undefined:
            self._new_value = clone(other)
            if self._old_value is undefined or ignore_old_value():
                return True
            return self._return(self.cmp(self._old_value, other))
        else:
            if not self.cmp(self._new_value, other):
                self._new_value = clone(other)

        return self._return(self.cmp(self._visible_value(), other))

    def _new_code(self):
        return self._file._value_to_code(self._new_value)

    def _get_changes(self) -> Iterator[Change]:
        new_token = value_to_token(self._new_value)
        if not self.cmp(self._old_value, self._new_value):
            flag = "fix"
        elif not self.cmp(self._new_value, self._old_value):
            flag = "trim"
        elif (
            self._ast_node is not None
            and self._file._token_of_node(self._ast_node) != new_token
        ):
            flag = "update"
        else:
            return

        new_code = self._file._token_to_code(new_token)

        yield Replace(
            node=self._ast_node,
            file=self._file,
            new_code=new_code,
            flag=flag,
            old_value=self._old_value,
            new_value=self._new_value,
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
