import ast
import inspect
from types import FrameType
from typing import Any
from typing import TypeVar

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._types import SnapshotRefBase

from ._global_state import state
from ._sentinels import undefined
from ._snapshot.snapshot_data import SnapshotData
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

    if Type is SnapshotReference:
        data = state().snapshots.get(key)
        new = Type(
            obj,
            frame,
            data=data if isinstance(data, SnapshotData) else None,
        )
        if data is None:
            state().snapshots[key] = new._data
        return new.result()

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
    def __init__(
        self, value, frame: FrameType, data: SnapshotData | None = None
    ) -> None:
        self._context = AdapterContext(frame)
        call_node = self._context.expr.node
        node = call_node.args[0] if call_node is not None and call_node.args else None
        if data is None:
            data = SnapshotData(explicit_dispatch=True)
        self._value = UndecidedValue(
            value,
            node,
            self._context,
            data,
            call_node=call_node,
        )
        self._data = self._value._data

    def result(self):
        return self._value

    @staticmethod
    def create_raw(obj, frame: FrameType):
        return obj

    def __repr__(self):
        if self._context.expr.node:
            return ast.unparse(self._context.expr.node)
        else:
            return "snapshot(...)"
