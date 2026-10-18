from __future__ import annotations

import ast
import inspect
import weakref
from ast import Call
from ast import Name
from pathlib import Path
from types import FrameType
from typing import Any
from typing import Iterator

from executing import Source

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._change import CallArg
from inline_snapshot._change import ChangeBase
from inline_snapshot._change import Delete
from inline_snapshot._compare_context import compare_context
from inline_snapshot._customize._custom_undefined import CustomUndefined
from inline_snapshot._customize._custom_unmanaged import CustomUnmanaged
from inline_snapshot._exceptions import UsageError
from inline_snapshot._generator_utils import split_gen
from inline_snapshot._generator_utils import with_flag
from inline_snapshot._global_state import state
from inline_snapshot._sentinels import undefined
from inline_snapshot._snapshot.snapshot_data import SnapshotData
from inline_snapshot._snapshot.snapshot_value import SnapshotValue
from inline_snapshot._types import Snapshot


class _NoDefault:
    pass


NoDefault = _NoDefault()


class SnapshotArgData(SnapshotData):
    """Snapshot state with a link to its current result facade."""

    reference: (
        SnapshotArgReference | weakref.ReferenceType[SnapshotArgReference] | None
    ) = None

    def _changes(self) -> Iterator[ChangeBase]:
        if isinstance(self.reference, weakref.ReferenceType):
            reference = self.reference()
        else:
            reference = self.reference

        if reference is not None and reference._value._defer_changes:
            reference._materialize_changes(self)
        return iter(self.changes)


def snapshot_arg(obj) -> Snapshot:
    """Captures a function argument value to generate snapshots at the call site.

    This function records the value of a function parameter and updates the
    **calling code** to pass that value as a snapshot. It's useful for recording
    what arguments should be passed to a function.

    Args:
        obj: The function parameter to capture. Must be a parameter of the
             function where snapshot_arg() is called.

    Returns:
        The original object when you use --inline-snapshot=disable.
        Otherwise, a snapshot reference that can be updated with --inline-snapshot.

    Example:
        <!-- inline-snapshot: first_block outcome-passed=1 outcome-errors=1 -->
        ``` python
        from inline_snapshot import snapshot_arg


        def get_stats(numbers, expected_sum=..., expected_max=..., expected_min=...):
            assert sum(numbers) == snapshot_arg(expected_sum)
            assert max(numbers) == snapshot_arg(expected_max)
            assert min(numbers) == snapshot_arg(expected_min)


        def test_example():
            get_stats([1, 2, 3])
        ```

        After running with `--inline-snapshot=create`:

        <!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
        ``` python hl_lines="11"
        from inline_snapshot import snapshot_arg


        def get_stats(numbers, expected_sum=..., expected_max=..., expected_min=...):
            assert sum(numbers) == snapshot_arg(expected_sum)
            assert max(numbers) == snapshot_arg(expected_max)
            assert min(numbers) == snapshot_arg(expected_min)


        def test_example():
            get_stats([1, 2, 3], expected_sum=6, expected_max=3, expected_min=1)
        ```

    """

    if isinstance(obj, SnapshotValue):
        return obj

    frame = inspect.currentframe()
    assert frame is not None
    frame = frame.f_back
    assert frame is not None

    if not state().active:
        if obj is undefined:
            raise AssertionError(
                "your snapshot is missing a value run pytest with --inline-snapshot=create"
            )
        return obj

    key = SnapshotArgReference.key_for(frame)
    data = state().snapshots.get(key)
    if not isinstance(data, SnapshotArgData):
        data = SnapshotArgData()
        state().snapshots[key] = data

    if isinstance(data.reference, weakref.ReferenceType):
        reference = data.reference()
    else:
        reference = data.reference
    if reference is None:
        reference = SnapshotArgReference(obj, frame, data)
        if reference._value._defer_changes:
            data.reference = reference
        else:
            data.reference = weakref.ref(reference)
    else:
        reference._re_eval(obj, frame)
    return reference.result()


def _get_call_frame(frame):
    call_frame = frame.f_back
    assert call_frame

    def get_origin():
        return (Path(call_frame.f_code.co_filename).name, call_frame.f_code.co_name)

    while get_origin() in [
        ("contextlib.py", "__enter__"),
        ("contextlib.py", "__exit__"),
    ]:
        call_frame = call_frame.f_back
        assert call_frame

    return call_frame


class SnapshotArgReference:
    _node: ast.expr | None
    _name: str
    _value: SnapshotValue
    _default_value: Any
    _arg_pos: int | None

    def __init__(self, value, frame: FrameType, data: SnapshotData):

        def check(cnd):
            if not cnd:
                raise UsageError(
                    "snapshot_arg() can only be called with function argument of the calling function as argument"
                )

        call_frame = _get_call_frame(frame)

        self._context = AdapterContext(call_frame)

        expr = Source.executing(frame)

        if expr.node is None:

            self._node = None

            self._value = SnapshotValue(
                value, None, self._context, data, on_change=self._refresh_changes
            )
            self._value._defer_changes = isinstance(
                self._value._old_value, CustomUnmanaged
            )
            self._default_value = ...
            self._name = "<unknown>"
            self._arg_pos = None
            return

        assert isinstance(expr.node, Call)
        check(len(expr.node.args) == 1)

        arg = expr.node.args[0]

        check(isinstance(arg, Name))
        assert isinstance(arg, Name)

        check(not expr.node.keywords)

        self._name = arg.id

        function: ast.AST = expr.node
        while not isinstance(
            function, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)
        ):
            function = function.parent  # type: ignore

        if isinstance(function, ast.Module):
            raise UsageError("snapshot_arg() can only be used inside functions")

        arg_pos = None
        pos_args = [*function.args.posonlyargs, *function.args.args]
        default: ast.expr | None = None

        for i, (func_arg, arg_default) in enumerate(
            zip(
                pos_args,
                [
                    *([None] * (len(pos_args) - len(function.args.defaults))),
                    *function.args.defaults,
                ],
            )
        ):
            if func_arg.arg == self._name:
                default = arg_default
                arg_pos = i
                break
        else:
            for func_arg, arg_default in zip(
                function.args.kwonlyargs, function.args.kw_defaults
            ):
                if func_arg.arg == self._name:
                    default = arg_default
                    break
            else:
                raise UsageError(
                    "the argument of snapshot_arg(...) has to be an argument of the calling function"
                )

        if default is None:
            self._default_value = NoDefault
        else:
            try:
                self._default_value = ast.literal_eval(default)
            except (ValueError, SyntaxError):
                raise UsageError(
                    f"snapshot_arg() only supports literal default values. "
                    f"unsupported default `{ast.unparse(default)}` for parameter '{self._name}'."
                )

        call_node = self._context.expr.node
        if isinstance(call_node, (ast.With, ast.AsyncWith)):
            if len(call_node.items) > 1:
                raise UsageError("only one with context expression is allowed")
            call_node = call_node.items[0].context_expr
            self._context.expr.node = call_node

        self._node = None

        if call_node is None:
            raise RuntimeError(
                "I did not found the calling code (context managers are not supported on cpython <3.11)"
            )

        self._arg_pos = arg_pos

        # For bound-method and constructor calls the implicit self/cls parameter
        # is counted in arg_pos but is absent from call_node.args at the call
        # site.  Detect this by checking whether the containing function lives
        # inside a ClassDef and is not decorated as @staticmethod.
        call_arg_pos = arg_pos
        if call_arg_pos is not None:
            parent = getattr(function, "parent", None)
            if isinstance(parent, ast.ClassDef):
                is_static = any(
                    (isinstance(d, ast.Name) and d.id == "staticmethod")
                    or (isinstance(d, ast.Attribute) and d.attr == "staticmethod")
                    for d in function.decorator_list
                )
                if not is_static and call_arg_pos > 0:
                    call_arg_pos -= 1

        if call_arg_pos is not None and len(call_node.args) > call_arg_pos:
            self._node = call_node.args[call_arg_pos]
        else:
            for kw in call_node.keywords:
                if kw.arg == self._name:
                    self._node = kw.value
                    break

        self._value = SnapshotValue(
            value,
            self._node,
            self._context,
            data,
            on_change=self._refresh_changes,
        )
        self._value._defer_changes = isinstance(self._value._old_value, CustomUnmanaged)

    @staticmethod
    def key_for(frame: FrameType):
        call_frame = _get_call_frame(frame)

        return (
            call_frame.f_code.co_filename,
            call_frame.f_code.co_firstlineno,
            call_frame.f_code.co_name,
            call_frame.f_lasti,
            frame.f_code.co_filename,
            frame.f_code.co_firstlineno,
            frame.f_code.co_name,
            frame.f_lasti,
        )

    def result(self):
        return self._value

    def _re_eval(self, obj, frame: FrameType) -> None:
        call_frame = _get_call_frame(frame)
        self._value._re_eval(obj, AdapterContext(call_frame))

    def _refresh_changes(self, data: SnapshotData, _context: AdapterContext) -> None:
        with compare_context():
            self._materialize_changes(data)

    def _materialize_changes(self, data: SnapshotData) -> None:
        changes: list[ChangeBase] = []

        new_value = self._value._new_value
        is_default = (
            not isinstance(new_value, CustomUndefined)
            and self._default_value is not NoDefault
            and self._default_value is not ...
            and new_value._eval() == self._default_value
        )

        if self._node is None:

            if self._name == "<unknown>":
                # executing could not locate the call site (e.g. Python ≤ 3.10
                # inside run_inline); we have no AST node and no arg name, so
                # we cannot generate a meaningful change.
                data.changes = []
                return

            if is_default:
                data.changes = []
                return

            flag = "create" if self._default_value is ... else "fix"

            rendered = split_gen(with_flag(self._value._new_code(), flag))
            changes.extend(rendered.list)
            new_code = rendered.value

            # The first positional argument can be inserted positionally;
            # any later position requires keyword form to avoid leaving gaps.
            if self._arg_pos == 0:
                changes.append(
                    CallArg(
                        flag=flag,
                        file=self._value._file,
                        node=self._context.expr.node,
                        arg_pos=0,
                        arg_name=None,
                        new_code=new_code,
                    )
                )
            else:

                changes.append(
                    CallArg(
                        flag=flag,
                        file=self._value._file,
                        node=self._context.expr.node,
                        arg_pos=None,
                        arg_name=self._name,
                        new_code=new_code,
                    )
                )
        else:
            changes = list(self._value._get_changes())
            if is_default and not isinstance(self._value._old_value, CustomUnmanaged):
                changes = [
                    Delete("fix" if changes else "trim", self._value._file, self._node)
                ]

        data.changes = changes
