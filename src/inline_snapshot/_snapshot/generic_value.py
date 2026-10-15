import ast
from typing import Generator
from typing import Iterator

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._code_repr import mock_repr
from inline_snapshot._customize._builder import Builder
from inline_snapshot._customize._custom import Custom
from inline_snapshot._customize._custom_undefined import CustomUndefined
from inline_snapshot._exceptions import ValueNotFound
from inline_snapshot._new_adapter import reeval

from .._change import ChangeBase
from .._global_state import state
from .._types import SnapshotBase
from .._unmanaged import declare_unmanaged
from .snapshot_data import SnapshotData


def ignore_old_value():
    return state().update_flags.fix or state().update_flags.update


@declare_unmanaged
class GenericValue(SnapshotBase):
    _current_op = "undefined"
    _ast_node: ast.expr | None
    _context: AdapterContext

    def __init__(
        self,
        data: SnapshotData,
        ast_node: ast.expr | None,
        context: AdapterContext,
        *,
        call_node=None,
        parent=None,
        parent_key=None,
        eager_changes=False,
    ):
        self._data = data
        self._ast_node = ast_node
        self._context = context
        self._call_node = call_node
        self._parent = parent
        self._parent_key = parent_key
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

    @property
    def _operation_changes(self):
        return self._data.operation_changes

    @_operation_changes.setter
    def _operation_changes(self, value):
        self._data.operation_changes = value

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

    def _select(self, operation: str, value_type):
        __tracebackhide__ = True
        if self._data.operation is None:
            self._data.operation = operation
        elif self._data.operation != operation:
            current_op = {
                "eq": "x == snapshot",
                "min": "x >= snapshot",
                "max": "x <= snapshot",
                "collection": "x in snapshot",
                "dict": "snapshot[key]",
            }[self._data.operation]
            requested_op = {
                "eq": "==",
                "min": "<=",
                "max": ">=",
                "collection": "in",
                "dict": "snapshot[key]",
            }[operation]
            raise TypeError(
                f"This snapshot cannot be use with `{requested_op}`, "
                f"because it was previously used with `{current_op}`"
            )
        return value_type(
            self._data,
            self._ast_node,
            self._context,
            call_node=self._call_node,
            parent=self._parent,
            parent_key=self._parent_key,
            eager_changes=self._eager_changes,
        )

    def _refresh_changes(self):
        if not self._eager_changes:
            return

        missing_argument = (
            isinstance(self._old_value, CustomUndefined)
            if self._call_node is None
            else not self._call_node.args
        )

        if self._parent is not None:
            if isinstance(self._old_value, CustomUndefined):
                from inline_snapshot._generator_utils import split_gen

                self._data.rendered_new_code = split_gen(self._new_code()).value
                self._data.changes = []
            else:
                self._data.changes = list(self._get_changes())
        else:
            if missing_argument:
                if isinstance(self._new_value, CustomUndefined):
                    self._data.changes = []
                else:
                    from inline_snapshot._change import CallArg
                    from inline_snapshot._generator_utils import split_gen

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
            else:
                self._data.changes = list(self._get_changes())

        if self._parent is not None:
            self._parent._child_changed(self._parent_key, self._data, self._context)

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
        raise NotImplementedError()

    def _new_code(self) -> Generator[ChangeBase, None, str]:
        raise NotImplementedError()

    def __repr__(self):
        return repr(self._visible_value()._eval())

    def _type_error(self, op):
        __tracebackhide__ = True
        raise TypeError(
            f"This snapshot cannot be use with `{op}`, because it was previously used with `{self._current_op}`"
        )

    def __eq__(self, other):
        __tracebackhide__ = True
        self._type_error("==")

    def __le__(self, other):
        __tracebackhide__ = True
        self._type_error("<=")

    def __ge__(self, other):
        __tracebackhide__ = True
        self._type_error(">=")

    def __contains__(self, item):
        __tracebackhide__ = True
        self._type_error("in")

    def __getitem__(self, item):
        __tracebackhide__ = True
        self._type_error("snapshot[key]")
