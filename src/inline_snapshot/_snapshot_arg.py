import ast
from ast import Call
from ast import Name
from types import FrameType
from typing import Iterator

from executing import Source

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._change import CallArg
from inline_snapshot._change import ChangeBase
from inline_snapshot._customize._custom_undefined import CustomUndefined
from inline_snapshot._exceptions import UsageError
from inline_snapshot._generator_utils import with_flag
from inline_snapshot._global_state import state
from inline_snapshot._inline_snapshot import create_snapshot
from inline_snapshot._snapshot.undecided_value import UndecidedValue
from inline_snapshot._types import Snapshot
from inline_snapshot._types import SnapshotRefBase


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
        <!-- inline-snapshot: first_block outcome-failed=1 -->
        ``` python
        from inline_snapshot._snapshot_arg import snapshot_arg


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
        from inline_snapshot._snapshot_arg import snapshot_arg


        def get_stats(numbers, expected_sum=..., expected_max=..., expected_min=...):
            assert sum(numbers) == snapshot_arg(expected_sum)
            assert max(numbers) == snapshot_arg(expected_max)
            assert min(numbers) == snapshot_arg(expected_min)


        def test_example():
            get_stats([1, 2, 3], expected_sum=6, expected_max=3, expected_min=1)
        ```

    """

    if not (
        state().active and (state().update_flags.fix or state().update_flags.create)
    ):
        return obj

    return create_snapshot(SnapshotArgReference, obj)


class SnapshotArgReference(SnapshotRefBase):
    def __init__(self, value, frame: FrameType):

        def check(cnd):
            if not cnd:
                raise UsageError(
                    "snapshot_arg() can only be called with function argument of the calling function as argument"
                )

        expr = Source.executing(frame)

        assert isinstance(expr.node, Call)
        check(len(expr.node.args) == 1)

        arg = expr.node.args[0]

        check(isinstance(arg, Name))
        assert isinstance(arg, Name)

        check(not expr.node.keywords)

        self._name = arg.id

        function = expr.node
        while not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function = function.parent

        arg_pos = None
        for i, arg in enumerate([*function.args.posonlyargs, *function.args.args]):
            if arg.arg == self._name:
                arg_pos = i

        call_frame = frame.f_back
        assert call_frame

        context = AdapterContext(call_frame)
        call_node = context.expr.node

        node = None

        if call_node is not None:
            if arg_pos is not None and len(call_node.args) > arg_pos:
                node = call_node.args[arg_pos]
            else:
                for kw in call_node.keywords:
                    if kw.arg == self._name:
                        node = kw.value

        self._node = node

        self._value = UndecidedValue(value, node, context)
        self._context = context

    @staticmethod
    def key_for(frame: FrameType):
        call_frame = frame.f_back
        assert call_frame

        return (
            id(call_frame.f_code),
            call_frame.f_lasti,
            id(frame.f_code),
            frame.f_lasti,
        )

    def result(self):
        return self._value

    @staticmethod
    def create_raw(obj, frame: FrameType):
        return obj

    def _changes(self) -> Iterator[ChangeBase]:

        if self._node is None:

            if isinstance(self._value._new_value, CustomUndefined):
                return

            new_code = yield from with_flag(self._value._new_code(), "create")

            yield CallArg(
                flag="create",
                file=self._value._file,
                node=self._context.expr.node,
                arg_pos=None,
                arg_name=self._name,
                new_code=new_code,
                new_value=self._value._new_value,
            )

        else:

            yield from self._value._get_changes()

    def _re_eval(self, obj, frame: FrameType):
        call_frame = frame.f_back
        assert call_frame
        self._value._re_eval(obj, AdapterContext(call_frame))
