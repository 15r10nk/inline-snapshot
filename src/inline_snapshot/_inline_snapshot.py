import inspect
from types import FrameType
from typing import Any
from typing import Iterator
from typing import TypeVar
from typing import cast

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._customize._custom_undefined import CustomUndefined
from inline_snapshot._generator_utils import with_flag
from inline_snapshot._types import SnapshotRefBase

from ._change import CallArg
from ._change import ChangeBase
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

    for _ in range(extra_frames + 2):
        frame = frame.f_back
        assert frame is not None

    if not state().active:
        if obj is undefined:
            raise AssertionError(
                "your snapshot is missing a value run pytest with --inline-snapshot=create"
            )
        else:
            return Type.create_raw(obj, frame)

    key = Type.key_for(frame)

    if key not in state().snapshots:
        new = Type(obj, frame)
        state().snapshots[key] = new
    else:
        new = state().snapshots[key]
        new._re_eval(obj, frame)

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
    def __init__(self, value, frame: FrameType):
        self._context = AdapterContext(frame)
        call_node = self._context.expr.node
        node = call_node.args[0] if call_node is not None and call_node.args else None
        self._value = UndecidedValue(value, node, self._context)

    def result(self):
        return self._value

    @staticmethod
    def create_raw(obj, frame: FrameType):
        return obj

    def __repr__(self):
        if self._expr:
            return ast.unparse(self._expr.node)
        else:
            return "snapshot(...)"

    def _changes(self) -> Iterator[ChangeBase]:

        if (
            isinstance(self._value._old_value, CustomUndefined)
            if self._context.expr.node is None
            else not self._context.expr.node.args
        ):

            if isinstance(self._value._new_value, CustomUndefined):
                return

            new_code = yield from with_flag(self._value._new_code(), "create")

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

            yield from self._value._get_changes()

    def _re_eval(self, obj, frame: FrameType):
        self._value._re_eval(obj, AdapterContext(frame))
