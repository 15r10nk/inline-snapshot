import ast
from typing import Iterator

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._customize import Builder
from inline_snapshot._customize import Custom
from inline_snapshot._customize import CustomUndefined
from inline_snapshot._new_adapter import reeval

from .._change import Change
from .._global_state import state
from .._types import SnapshotBase
from .._unmanaged import declare_unmanaged


def ignore_old_value():
    return state().update_flags.fix or state().update_flags.update


@declare_unmanaged
class GenericValue(SnapshotBase):
    _new_value: Custom
    _old_value: Custom
    _current_op = "undefined"
    _ast_node: ast.Expr
    _context: AdapterContext

    def _return(self, result, new_result=True):

        if not result:
            state().incorrect_values += 1
        flags = state().update_flags

        if (
            flags.fix
            or flags.create
            or flags.update
            or isinstance(self._old_value, CustomUndefined)
        ):
            return new_result
        return result

    @property
    def _file(self):
        return self._context.file

    def _re_eval(self, value, context: AdapterContext):

        self._old_value = reeval(self._old_value, Builder()._get_handler(value))
        return

    def _ignore_old(self):
        return (
            state().update_flags.fix
            or state().update_flags.update
            or state().update_flags.create
            or isinstance(self._old_value, CustomUndefined)
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
        return repr(self._visible_value().eval())

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
