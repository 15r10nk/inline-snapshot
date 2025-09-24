import ast
import inspect
from typing import Any
from typing import Iterator
from typing import TypeVar
from typing import cast

from executing import Source

from inline_snapshot._source_file import SourceFile
from inline_snapshot._types import SnapshotRefBase

from ._adapter.adapter import AdapterContext
from ._adapter.adapter import FrameContext
from ._change import CallArg
from ._change import Change
from ._global_state import state
from ._sentinels import undefined
from ._snapshot.undecided_value import UndecidedValue


class ReprWrapper:
    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def __repr__(self):
        return self.func.__name__


_T = TypeVar("_T")


def repr_wrapper(func: _T) -> _T:
    return ReprWrapper(func)  # type: ignore


def create_snapshot(Type, obj, extra_frames=0):

    frame = inspect.currentframe()
    assert frame is not None
    frame = frame.f_back
    assert frame is not None
    frame = frame.f_back
    assert frame is not None

    for _ in range(extra_frames):
        frame = frame.f_back
        assert frame is not None

    expr = Source.executing(frame)

    source = cast(Source, getattr(expr, "source", None) if expr is not None else None)
    context = AdapterContext(
        file=SourceFile(source),
        frame=FrameContext(globals=frame.f_globals, locals=frame.f_locals),
        qualname=expr.code_qualname(),
    )

    if not state().active:
        if obj is undefined:
            raise AssertionError(
                "your snapshot is missing a value run pytest with --inline-snapshot=create"
            )
        else:
            return Type.create_raw(obj, context)

    key = id(frame.f_code), frame.f_lasti

    if key not in state().snapshots:
        node = expr.node
        if node is None:
            # we can run without knowing of the calling expression but we will not be able to fix code
            new = Type(obj, None, context)
            state().snapshots[key] = Type(obj, None, context)
        else:
            assert isinstance(node, ast.Call)
            new = Type(obj, expr, context)
        state().snapshots[key] = new
    else:
        new = state().snapshots[key]
        new._re_eval(obj, context)

    return new.result()


@repr_wrapper
def snapshot(obj: Any = undefined) -> Any:
    """`snapshot()` is a placeholder for some value.

    `pytest --inline-snapshot=create` will create the value which matches your conditions.

    >>> assert 5 == snapshot()
    >>> assert 5 <= snapshot()
    >>> assert 5 >= snapshot()
    >>> assert 5 in snapshot()

    `snapshot()[key]` can be used to create sub-snapshots.

    The generated value will be inserted as argument to `snapshot()`

    >>> assert 5 == snapshot(5)

    `snapshot(value)` has general the semantic of an noop which returns `value`.
    """

    return create_snapshot(SnapshotReference, obj, 1)


class SnapshotReference(SnapshotRefBase):
    def __init__(self, value, expr, context: AdapterContext):
        self._expr = expr
        node = expr.node.args[0] if expr is not None and expr.node.args else None
        self._value = UndecidedValue(value, node, context)
        self._context = context

    def result(self):
        return self._value

    @staticmethod
    def create_raw(obj, context: AdapterContext):
        return obj

    def _changes(self) -> Iterator[Change]:

        if (
            self._value._old_value is undefined
            if self._expr is None
            else not self._expr.node.args
        ):

            if self._value._new_value is undefined:
                return

            new_code = self._value._new_code()

            yield CallArg(
                flag="create",
                file=self._value._file,
                node=self._expr.node if self._expr is not None else None,
                arg_pos=0,
                arg_name=None,
                new_code=new_code,
                new_value=self._value._new_value,
            )

        else:

            yield from self._value._get_changes()

    def _re_eval(self, obj, context: AdapterContext):
        self._value._re_eval(obj, context)
