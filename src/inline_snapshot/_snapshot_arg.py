import ast
from ast import Call
from ast import Name
from pathlib import Path
from types import FrameType
from typing import Any
from typing import Iterator
from typing import Optional

from executing import Source

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._change import CallArg
from inline_snapshot._change import ChangeBase
from inline_snapshot._change import Delete
from inline_snapshot._customize._custom_undefined import CustomUndefined
from inline_snapshot._exceptions import UsageError
from inline_snapshot._generator_utils import with_flag
from inline_snapshot._inline_snapshot import create_snapshot
from inline_snapshot._snapshot.generic_value import GenericValue
from inline_snapshot._snapshot.undecided_value import UndecidedValue
from inline_snapshot._types import Snapshot
from inline_snapshot._types import SnapshotRefBase


class NoDefault:
    pass


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

    # if not (
    #     state().active and (state().update_flags.fix or state().update_flags.create)
    # ):
    #     return obj

    if isinstance(obj, GenericValue):
        return obj

    return create_snapshot(SnapshotArgReference, obj)


def get_call_frame(frame):
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

    print(get_origin())
    return call_frame


class SnapshotArgReference(SnapshotRefBase):
    _node: Optional[ast.expr]
    _name: str
    _value: GenericValue
    _default_value: Any

    def __init__(self, value, frame: FrameType):

        def check(cnd):
            if not cnd:
                raise UsageError(
                    "snapshot_arg() can only be called with function argument of the calling function as argument"
                )

        call_frame = get_call_frame(frame)

        self._context = AdapterContext(call_frame)

        expr = Source.executing(frame)

        if expr.node is None:

            self._node = None

            self._value = UndecidedValue(value, None, self._context)
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
        default: Optional[ast.expr] = None

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
            self._default_value = NoDefault()
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

        assert call_node is not None
        self._arg_pos = arg_pos

        if arg_pos is not None and len(call_node.args) > arg_pos:
            self._node = call_node.args[arg_pos]
        else:
            for kw in call_node.keywords:
                if kw.arg == self._name:
                    self._node = kw.value
                    break

        self._value = UndecidedValue(value, self._node, self._context)

    @staticmethod
    def key_for(frame: FrameType):
        call_frame = get_call_frame(frame)

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

        new_value = self._value._new_value
        is_default = (
            not isinstance(new_value, CustomUndefined)
            and not isinstance(self._default_value, NoDefault)
            and self._default_value is not ...
            and new_value._eval() == self._default_value
        )

        if self._node is None:

            if isinstance(self._value._new_value, CustomUndefined):
                return

            if is_default:
                return

            new_code = yield from with_flag(self._value._new_code(), "create")

            if self._arg_pos == 0:
                yield CallArg(
                    flag="create",
                    file=self._value._file,
                    node=self._context.expr.node,
                    arg_pos=0,
                    arg_name=None,
                    new_code=new_code,
                    new_value=self._value._new_value,
                )
            else:

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
            if is_default:
                yield Delete("fix", self._value._file, self._node, None)
            else:
                yield from self._value._get_changes()

    def _re_eval(self, obj, frame: FrameType):
        call_frame = frame.f_back
        assert call_frame
        self._value._re_eval(obj, AdapterContext(call_frame))
