import ast
import copy
from typing import Any
from typing import Iterator

from .._adapter.adapter import AdapterContext
from .._adapter.adapter import get_adapter_type
from .._change import Change
from .._code_repr import code_repr
from .._exceptions import UsageError
from .._global_state import state
from .._sentinels import undefined
from .._types import Snapshot
from .._unmanaged import Unmanaged
from .._unmanaged import update_allowed


def clone(obj):
    new = copy.deepcopy(obj)
    if not obj == new:
        raise UsageError(
            f"""\
inline-snapshot uses `copy.deepcopy` to copy objects,
but the copied object is not equal to the original one:

value = {code_repr(obj)}
copied_value = copy.deepcopy(value)
assert value == copied_value

Please fix the way your object is copied or your __eq__ implementation.
"""
        )
    return new


def ignore_old_value():
    return state().update_flags.fix or state().update_flags.update


class GenericValue(Snapshot):
    _new_value: Any
    _old_value: Any
    _current_op = "undefined"
    _ast_node: ast.Expr
    _context: AdapterContext

    def _return(self, result, new_result=True):

        if not result:
            state().incorrect_values += 1
        flags = state().update_flags

        if flags.fix or flags.create or flags.update or self._old_value is undefined:
            return new_result
        return result

    @property
    def _file(self):
        return self._context.file

    def get_adapter(self, value):
        return get_adapter_type(value)(self._context)

    def _re_eval(self, value, context: AdapterContext):
        self._context = context

        def re_eval(old_value, node, value):
            if isinstance(old_value, Unmanaged):
                old_value.value = value
                return

            assert type(old_value) is type(value)

            adapter = self.get_adapter(old_value)
            if adapter is not None and hasattr(adapter, "items"):
                old_items = adapter.items(old_value, node)
                new_items = adapter.items(value, node)
                assert len(old_items) == len(new_items)

                for old_item, new_item in zip(old_items, new_items):
                    re_eval(old_item.value, old_item.node, new_item.value)

            else:
                if update_allowed(old_value):
                    if not old_value == value:
                        raise UsageError(
                            "snapshot value should not change. Use Is(...) for dynamic snapshot parts."
                        )
                else:
                    assert False, "old_value should be converted to Unmanaged"

        re_eval(self._old_value, self._ast_node, value)

    def _ignore_old(self):
        return (
            state().update_flags.fix
            or state().update_flags.update
            or state().update_flags.create
            or self._old_value is undefined
        )

    def _visible_value(self):
        if self._ignore_old():
            return self._new_value
        else:
            return self._old_value

    def _get_changes(self) -> Iterator[Change]:
        raise NotImplementedError()

    def _new_code(self):
        raise NotImplementedError()

    def __repr__(self):
        return repr(self._visible_value())

    def _type_error(self, op):
        __tracebackhide__ = True
        raise TypeError(
            f"This snapshot cannot be use with `{op}`, because it was previously used with `{self._current_op}`"
        )

    def __eq__(self, _other):
        __tracebackhide__ = True
        self._type_error("==")

    def __le__(self, _other):
        __tracebackhide__ = True
        self._type_error("<=")

    def __ge__(self, _other):
        __tracebackhide__ = True
        self._type_error(">=")

    def __contains__(self, _other):
        __tracebackhide__ = True
        self._type_error("in")

    def __getitem__(self, _item):
        __tracebackhide__ = True
        self._type_error("snapshot[key]")
