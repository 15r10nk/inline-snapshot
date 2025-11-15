from typing import Iterator

import pytest

from inline_snapshot._customize import Builder
from inline_snapshot._customize import CustomUndefined

from .._change import Change
from .._change import Replace
from .._global_state import state
from .._utils import value_to_token
from .generic_value import GenericValue
from .generic_value import ignore_old_value


class MinMaxValue(GenericValue):
    """Generic implementation for <=, >="""

    @staticmethod
    def cmp(a, b):
        raise NotImplementedError

    def _generic_cmp(self, other):
        pytest.skip()
        if isinstance(self._old_value, CustomUndefined):
            state().missing_values += 1

        if isinstance(self._new_value, CustomUndefined):
            self._new_value = Builder().get_handler(other)
            if isinstance(self._old_value, CustomUndefined) or ignore_old_value():
                return True
            return self._return(self.cmp(self._old_value.eval(), other))
        else:
            if not self.cmp(self._new_value.eval(), other):
                self._new_value = Builder.get_handler(other)

        return self._return(self.cmp(self._visible_value().eval(), other))

    def _new_code(self):
        # TODO repr() ...
        return self._file._value_to_code(self._new_value.eval())

    def _get_changes(self) -> Iterator[Change]:
        pytest.skip()
        # TODO repr() ...
        new_token = value_to_token(self._new_value.eval())

        if not self.cmp(self._old_value.eval(), self._new_value.eval()):
            flag = "fix"
        elif not self.cmp(self._new_value.eval(), self._old_value.eval()):
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
            old_value=self._old_value.eval(),
            new_value=self._new_value.eval(),
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
