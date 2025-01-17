import ast
import copy
import inspect
from typing import Any
from typing import cast
from typing import Iterator
from typing import TypeVar

from executing import Source
from inline_snapshot._adapter.adapter import adapter_map
from inline_snapshot._source_file import SourceFile

from ._adapter.adapter import AdapterContext
from ._adapter.adapter import FrameContext
from ._adapter.adapter import get_adapter_type
from ._change import CallArg
from ._change import Change
from ._change import Replace
from ._code_repr import code_repr
from ._exceptions import UsageError
from ._sentinels import undefined
from ._snapshot.generic_value import GenericValue
from ._unmanaged import map_unmanaged
from ._unmanaged import Unmanaged
from ._utils import value_to_token
from .global_state import state


def ignore_old_value():
    return state()._update_flags.fix or state()._update_flags.update


class UndecidedValue(GenericValue):
    def __init__(self, old_value, ast_node, context: AdapterContext):

        old_value = adapter_map(old_value, map_unmanaged)
        self._old_value = old_value
        self._new_value = undefined
        self._ast_node = ast_node
        self._context = context

    def _change(self, cls):
        self.__class__ = cls

    def _new_code(self):
        assert False

    def _get_changes(self) -> Iterator[Change]:

        def handle(node, obj):

            adapter = get_adapter_type(obj)
            if adapter is not None and hasattr(adapter, "items"):
                for item in adapter.items(obj, node):
                    yield from handle(item.node, item.value)
                return

            if not isinstance(obj, Unmanaged) and node is not None:
                new_token = value_to_token(obj)
                if self._file._token_of_node(node) != new_token:
                    new_code = self._file._token_to_code(new_token)

                    yield Replace(
                        node=self._ast_node,
                        file=self._file,
                        new_code=new_code,
                        flag="update",
                        old_value=self._old_value,
                        new_value=self._old_value,
                    )

        if self._file._source is not None:
            yield from handle(self._ast_node, self._old_value)

    # functions which determine the type

    def __eq__(self, other):
        from ._snapshot.eq_value import EqValue

        self._change(EqValue)
        return self == other

    def __le__(self, other):
        from ._snapshot.min_max_value import MinValue

        self._change(MinValue)
        return self <= other

    def __ge__(self, other):
        from ._snapshot.min_max_value import MaxValue

        self._change(MaxValue)
        return self >= other

    def __contains__(self, other):
        from ._snapshot.collection_value import CollectionValue

        self._change(CollectionValue)
        return other in self

    def __getitem__(self, item):
        from ._snapshot.dict_value import DictValue

        self._change(DictValue)
        return self[item]


def clone(obj):
    new = copy.deepcopy(obj)
    if not obj == new:
        raise UsageError(
            f"""\
inline-snapshot uses `copy.deepcopy` to copy objects,
but the copied object is not equal to the original one:

original: {code_repr(obj)}
copied:   {code_repr(new)}

Please fix the way your object is copied or your __eq__ implementation.
"""
        )
    return new


T = TypeVar("T")


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
    if not state()._active:
        if obj is undefined:
            raise AssertionError(
                "your snapshot is missing a value run pytest with --inline-snapshot=create"
            )
        else:
            return obj

    frame = inspect.currentframe()
    assert frame is not None
    frame = frame.f_back
    assert frame is not None
    frame = frame.f_back
    assert frame is not None

    expr = Source.executing(frame)

    source = cast(Source, getattr(expr, "source", None) if expr is not None else None)
    context = AdapterContext(
        file=SourceFile(source),
        frame=FrameContext(globals=frame.f_globals, locals=frame.f_locals),
    )

    module = inspect.getmodule(frame)
    if module is not None and module.__file__ is not None:
        state()._files_with_snapshots.add(module.__file__)

    key = id(frame.f_code), frame.f_lasti

    if key not in state().snapshots:
        node = expr.node
        if node is None:
            # we can run without knowing of the calling expression but we will not be able to fix code
            state().snapshots[key] = SnapshotReference(obj, None, context)
        else:
            assert isinstance(node, ast.Call)
            state().snapshots[key] = SnapshotReference(obj, expr, context)
    else:
        state().snapshots[key]._re_eval(obj, context)

    return state().snapshots[key]._value


def used_externals(tree):
    return [
        n.args[0].value
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "external"
        and n.args
        and isinstance(n.args[0], ast.Constant)
    ]


class SnapshotReference:
    def __init__(self, value, expr, context: AdapterContext):
        self._expr = expr
        node = expr.node.args[0] if expr is not None and expr.node.args else None
        source = expr.source if expr is not None else None
        self._value = UndecidedValue(value, node, context)

    def _changes(self):

        if self._value._old_value is undefined:

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
