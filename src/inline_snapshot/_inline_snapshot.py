import ast
import copy
import inspect
from typing import Any
from typing import Dict  # noqa
from typing import Iterator
from typing import List
from typing import Set
from typing import Tuple  # noqa
from typing import TypeVar

from executing import Source
from inline_snapshot._adapter.adapter import Adapter
from inline_snapshot._adapter.adapter import adapter_map
from inline_snapshot._source_file import SourceFile

from ._adapter import get_adapter_type
from ._change import CallArg
from ._change import Change
from ._change import Delete
from ._change import DictInsert
from ._change import ListInsert
from ._change import Replace
from ._code_repr import code_repr
from ._compare_context import compare_only
from ._exceptions import UsageError
from ._sentinels import undefined
from ._types import Category
from ._types import Snapshot
from ._unmanaged import map_unmanaged
from ._unmanaged import Unmanaged
from ._unmanaged import update_allowed
from ._utils import value_to_token


snapshots = {}  # type: Dict[Tuple[int, int], SnapshotReference]

_active = False

_files_with_snapshots: Set[str] = set()

_missing_values = 0
_incorrect_values = 0


def _return(result):
    global _incorrect_values
    if not result:
        _incorrect_values += 1
    return result


class Flags:
    """
    fix: the value needs to be changed to pass the tests
    update: the value should be updated because the token-stream has changed
    create: the snapshot is empty `snapshot()`
    trim: the snapshot contains more values than neccessary. 1 could be trimmed in `5 in snapshot([1,5])`.
    """

    def __init__(self, flags: Set[Category] = set()):
        self.fix = "fix" in flags
        self.update = "update" in flags
        self.create = "create" in flags
        self.trim = "trim" in flags

    def to_set(self):
        return {k for k, v in self.__dict__.items() if v}

    def __repr__(self):
        return f"Flags({self.to_set()})"


_update_flags = Flags()


def ignore_old_value():
    return _update_flags.fix or _update_flags.update


class GenericValue(Snapshot):
    _new_value: Any
    _old_value: Any
    _current_op = "undefined"
    _ast_node: ast.Expr
    _file: SourceFile

    def get_adapter(self, value):
        return get_adapter_type(value)(self._file)

    def _re_eval(self, value):

        def re_eval(old_value, node, value):
            if isinstance(old_value, Unmanaged):
                old_value.value = value
                return

            assert type(old_value) is type(value)

            adapter = self.get_adapter(old_value)
            if adapter is not None and hasattr(adapter, "items"):
                old_items = adapter.items(old_value, node)
                new_items = adapter.items(value, node)
                assert len(old_items) == len(new_items)

                for old_item, new_item in zip(old_items, new_items):
                    re_eval(old_item.value, old_item.node, new_item.value)

            else:
                if update_allowed(old_value):
                    if not old_value == value:
                        raise UsageError(
                            "snapshot value should not change. Use Is(...) for dynamic snapshot parts."
                        )
                else:
                    assert False, "old_value should be converted to Unmanaged"

        re_eval(self._old_value, self._ast_node, value)

    def _ignore_old(self):
        return (
            _update_flags.fix
            or _update_flags.update
            or _update_flags.create
            or self._old_value is undefined
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
        return repr(self._visible_value())

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


class UndecidedValue(GenericValue):
    def __init__(self, old_value, ast_node, source):

        old_value = adapter_map(old_value, map_unmanaged)
        self._old_value = old_value
        self._new_value = undefined
        self._ast_node = ast_node
        self._file = SourceFile(source)

    def _change(self, cls):
        self.__class__ = cls

    def _new_code(self):
        assert False

    def _get_changes(self) -> Iterator[Change]:

        def handle(node, obj):

            adapter = self.get_adapter(obj)
            if adapter is not None and hasattr(adapter, "items"):
                for item in adapter.items(obj, node):
                    yield from handle(item.node, item.value)
                return

            if not isinstance(obj, Unmanaged):
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
        self._change(EqValue)
        return self == other

    def __le__(self, other):
        self._change(MinValue)
        return self <= other

    def __ge__(self, other):
        self._change(MaxValue)
        return self >= other

    def __contains__(self, other):
        self._change(CollectionValue)
        return other in self

    def __getitem__(self, item):
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


class EqValue(GenericValue):
    _current_op = "x == snapshot"
    _changes: List[Change]

    def __eq__(self, other):
        global _missing_values
        if self._old_value is undefined:
            _missing_values += 1

        if not compare_only() and self._new_value is undefined:
            adapter = Adapter(self._file).get_adapter(self._old_value, other)
            it = iter(adapter.assign(self._old_value, self._ast_node, clone(other)))
            self._changes = []
            while True:
                try:
                    self._changes.append(next(it))
                except StopIteration as ex:
                    self._new_value = ex.value
                    break

        return _return(self._visible_value() == other)

        # if self._new_value is undefined:
        #     self._new_value = use_valid_old_values(self._old_value, clone(other))
        #     if self._old_value is undefined or ignore_old_value():
        #         return True
        #     return _return(self._old_value == other)
        # else:
        #     return _return(self._new_value == other)

    def _new_code(self):
        return self._file._value_to_code(self._new_value)

    def _get_changes(self) -> Iterator[Change]:
        return iter(self._changes)


class MinMaxValue(GenericValue):
    """Generic implementation for <=, >="""

    @staticmethod
    def cmp(a, b):
        raise NotImplemented

    def _generic_cmp(self, other):
        global _missing_values
        if self._old_value is undefined:
            _missing_values += 1

        if self._new_value is undefined:
            self._new_value = clone(other)
            if self._old_value is undefined or ignore_old_value():
                return True
            return _return(self.cmp(self._old_value, other))
        else:
            if not self.cmp(self._new_value, other):
                self._new_value = clone(other)

        return _return(self.cmp(self._visible_value(), other))

    def _new_code(self):
        return self._file._value_to_code(self._new_value)

    def _get_changes(self) -> Iterator[Change]:
        new_token = value_to_token(self._new_value)
        if not self.cmp(self._old_value, self._new_value):
            flag = "fix"
        elif not self.cmp(self._new_value, self._old_value):
            flag = "trim"
        elif (
            self._ast_node is not None
            and self._file._token_of_node(self._ast_node) != new_token
        ):
            flag = "update"
        else:
            return

        new_code = self._file._token_to_code(new_token)

        yield Replace(
            node=self._ast_node,
            file=self._file,
            new_code=new_code,
            flag=flag,
            old_value=self._old_value,
            new_value=self._new_value,
        )


class MinValue(MinMaxValue):
    """
    handles:

    >>> snapshot(5) <= 6
    True

    >>> 6 >= snapshot(5)
    True

    """

    _current_op = "x >= snapshot"

    @staticmethod
    def cmp(a, b):
        return a <= b

    __le__ = MinMaxValue._generic_cmp


class MaxValue(MinMaxValue):
    """
    handles:

    >>> snapshot(5) >= 4
    True

    >>> 4 <= snapshot(5)
    True

    """

    _current_op = "x <= snapshot"

    @staticmethod
    def cmp(a, b):
        return a >= b

    __ge__ = MinMaxValue._generic_cmp


class CollectionValue(GenericValue):
    _current_op = "x in snapshot"

    def __contains__(self, item):
        global _missing_values
        if self._old_value is undefined:
            _missing_values += 1

        if self._new_value is undefined:
            self._new_value = [clone(item)]
        else:
            if item not in self._new_value:
                self._new_value.append(clone(item))

        if ignore_old_value() or self._old_value is undefined:
            return True
        else:
            return _return(item in self._old_value)

    def _new_code(self):
        return self._file._value_to_code(self._new_value)

    def _get_changes(self) -> Iterator[Change]:

        if self._ast_node is None:
            elements = [None] * len(self._old_value)
        else:
            assert isinstance(self._ast_node, ast.List)
            elements = self._ast_node.elts

        for old_value, old_node in zip(self._old_value, elements):
            if old_value not in self._new_value:
                yield Delete(
                    flag="trim",
                    file=self._file,
                    node=old_node,
                    old_value=old_value,
                )
                continue

            # check for update
            new_token = value_to_token(old_value)

            if (
                old_node is not None
                and self._file._token_of_node(old_node) != new_token
            ):
                new_code = self._file._token_to_code(new_token)

                yield Replace(
                    node=old_node,
                    file=self._file,
                    new_code=new_code,
                    flag="update",
                    old_value=old_value,
                    new_value=old_value,
                )

        new_values = [v for v in self._new_value if v not in self._old_value]
        if new_values:
            yield ListInsert(
                flag="fix",
                file=self._file,
                node=self._ast_node,
                position=len(self._old_value),
                new_code=[self._file._value_to_code(v) for v in new_values],
                new_values=new_values,
            )


class DictValue(GenericValue):
    _current_op = "snapshot[key]"

    def __getitem__(self, index):
        global _missing_values

        if self._new_value is undefined:
            self._new_value = {}

        if index not in self._new_value:
            old_value = self._old_value
            if old_value is undefined:
                _missing_values += 1
                old_value = {}

            child_node = None
            if self._ast_node is not None:
                assert isinstance(self._ast_node, ast.Dict)
                if index in old_value:
                    pos = list(old_value.keys()).index(index)
                    child_node = self._ast_node.values[pos]

            self._new_value[index] = UndecidedValue(
                old_value.get(index, undefined), child_node, self._file
            )

        return self._new_value[index]

    def _re_eval(self, value):
        super()._re_eval(value)

        if self._new_value is not undefined and self._old_value is not undefined:
            for key, s in self._new_value.items():
                if key in self._old_value:
                    s._re_eval(self._old_value[key])

    def _new_code(self):
        return (
            "{"
            + ", ".join(
                [
                    f"{self._file._value_to_code(k)}: {v._new_code()}"
                    for k, v in self._new_value.items()
                    if not isinstance(v, UndecidedValue)
                ]
            )
            + "}"
        )

    def _get_changes(self) -> Iterator[Change]:

        assert self._old_value is not undefined

        if self._ast_node is None:
            values = [None] * len(self._old_value)
        else:
            assert isinstance(self._ast_node, ast.Dict)
            values = self._ast_node.values

        for key, node in zip(self._old_value.keys(), values):
            if key in self._new_value:
                # check values with same keys
                yield from self._new_value[key]._get_changes()
            else:
                # delete entries
                yield Delete("trim", self._file, node, self._old_value[key])

        to_insert = []
        for key, new_value_element in self._new_value.items():
            if key not in self._old_value and not isinstance(
                new_value_element, UndecidedValue
            ):
                # add new values
                to_insert.append((key, new_value_element._new_code()))

        if to_insert:
            new_code = [(self._file._value_to_code(k), v) for k, v in to_insert]
            yield DictInsert(
                "create",
                self._file,
                self._ast_node,
                len(self._old_value),
                new_code,
                to_insert,
            )


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
    if not _active:
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

    module = inspect.getmodule(frame)
    if module is not None and module.__file__ is not None:
        _files_with_snapshots.add(module.__file__)

    key = id(frame.f_code), frame.f_lasti

    if key not in snapshots:
        node = expr.node
        if node is None:
            # we can run without knowing of the calling expression but we will not be able to fix code
            snapshots[key] = SnapshotReference(obj, None)
        else:
            assert isinstance(node, ast.Call)
            snapshots[key] = SnapshotReference(obj, expr)
    else:
        snapshots[key]._re_eval(obj)

    return snapshots[key]._value


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
    def __init__(self, value, expr):
        self._expr = expr
        node = expr.node.args[0] if expr is not None and expr.node.args else None
        source = expr.source if expr is not None else None
        self._value = UndecidedValue(value, node, source)
        self._uses_externals = []

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

    def _re_eval(self, obj):
        self._value._re_eval(obj)
