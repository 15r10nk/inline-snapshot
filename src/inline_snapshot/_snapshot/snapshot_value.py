import ast
from collections.abc import Callable
from typing import Generator
from typing import Iterator

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._code_repr import mock_repr
from inline_snapshot._customize._builder import Builder
from inline_snapshot._customize._custom import Custom
from inline_snapshot._customize._custom_undefined import CustomUndefined
from inline_snapshot._exceptions import ValueNotFound
from inline_snapshot._generator_utils import split_gen
from inline_snapshot._new_adapter import reeval

from .._change import CallArg
from .._change import ChangeBase
from .._global_state import state
from .._types import SnapshotBase
from .._unmanaged import declare_unmanaged
from .snapshot_data import SnapshotData


def ignore_old_value():
    return state().update_flags.fix or state().update_flags.update


@declare_unmanaged
class SnapshotValue(SnapshotBase):
    _ast_node: ast.expr | None
    _context: AdapterContext

    def __init__(
        self,
        data: SnapshotData,
        ast_node: ast.expr | None,
        context: AdapterContext,
        *,
        call_node: ast.Call | None = None,
        on_change: Callable[[SnapshotData, AdapterContext], None] | None = None,
        eager_changes: bool = False,
    ):
        self._data = data
        self._ast_node = ast_node
        self._context = context
        self._call_node = call_node
        self._on_change = on_change
        # snapshot() materializes report changes while this context is alive.
        # snapshot_arg() still uses its legacy session-end materialization.
        self._eager_changes = eager_changes

    @property
    def _old_value(self):
        return self._data._old_value

    @_old_value.setter
    def _old_value(self, value):
        self._data._old_value = value

    @property
    def _new_value(self):
        return self._data._new_value

    @_new_value.setter
    def _new_value(self, value):
        self._data._new_value = value

    def get_builder(self, **args):
        return Builder(_snapshot_context=self._context, **args)

    def _return(self, result, new_result=True):

        if not result:
            state().incorrect_values += 1
        flags = state().update_flags

        if (
            flags.fix
            or flags.create
            #            or flags.trim
            or flags.update
            or isinstance(self._old_value, CustomUndefined)
        ):
            return new_result
        return result

    def _load_value(self, which) -> Custom:

        if which == "new" and not isinstance(self._new_value, CustomUndefined):
            return self._new_value
        elif which == "old" and not isinstance(self._old_value, CustomUndefined):
            return self._old_value

        raise ValueNotFound

    @property
    def _file(self):
        return self._context.file

    def to_custom(self, value, **args):
        with mock_repr(self._context):
            return self.get_builder(**args)._customize_all(value)

    def value_to_custom(self, value):
        if isinstance(value, Custom):
            return value

        if self._ast_node is None:
            from inline_snapshot._snapshot.undecided_value import ValueToCustom

            return ValueToCustom(self._context).convert(value)
        else:
            from inline_snapshot._snapshot.undecided_value import AstToCustom

            return AstToCustom(self._context).convert(value, self._ast_node)

    def _re_eval(self, value, context: AdapterContext):
        self._context = context

        self._old_value = reeval(self._old_value, self.value_to_custom(value))

    def _refresh_changes(self):
        if not self._eager_changes:
            return

        if self._on_change is not None:
            self._refresh_child_changes()
            self._on_change(self._data, self._context)
        elif self._missing_argument():
            self._refresh_create_changes()
        else:
            self._data.changes = list(self._get_changes())

    def _missing_argument(self):
        if self._call_node is None:
            return isinstance(self._old_value, CustomUndefined)
        return not self._call_node.args

    def _refresh_child_changes(self):
        if isinstance(self._old_value, CustomUndefined):
            self._data.rendered_new_code = split_gen(self._new_code()).value
            self._data.changes = []
        else:
            self._data.changes = list(self._get_changes())

    def _refresh_create_changes(self):
        if isinstance(self._new_value, CustomUndefined):
            self._data.changes = []
            return

        rendered = split_gen(self._new_code())
        self._data.rendered_new_code = rendered.value
        for change in rendered.list:
            change.flag = "create"
        self._data.changes = [
            *rendered.list,
            CallArg(
                flag="create",
                file=self._file,
                node=self._call_node,
                arg_pos=0,
                arg_name=None,
                new_code=rendered.value,
            ),
        ]

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

    def _get_changes(self) -> Iterator[ChangeBase]:
        if self._data.operation is None:
            return iter(())
        return self._data.operation._get_changes(self)

    def _new_code(self) -> Generator[ChangeBase, None, str]:
        assert self._data.operation is not None
        return self._data.operation._new_code(self)

    def __repr__(self):
        return repr(self._visible_value()._eval())

    def __eq__(self, other):
        __tracebackhide__ = True
        from .._compare_context import compare_only
        from ._operation.eq_operation import EqOperation

        if compare_only():
            return False
        return self._data.use(EqOperation).compare(self, other)

    def __le__(self, other):
        __tracebackhide__ = True
        from ._operation.min_max_operation import MinOperation

        return self._data.use(MinOperation).compare(self, other)

    def __ge__(self, other):
        __tracebackhide__ = True
        from ._operation.min_max_operation import MaxOperation

        return self._data.use(MaxOperation).compare(self, other)

    def __contains__(self, item):
        __tracebackhide__ = True
        from ._operation.collection_operation import CollectionOperation

        return self._data.use(CollectionOperation).contains(self, item)

    def __getitem__(self, item):
        __tracebackhide__ = True
        from ._operation.dict_operation import DictOperation

        return self._data.use(DictOperation).getitem(self, item)
