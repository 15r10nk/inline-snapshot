import ast
import contextlib
import inspect
from collections import defaultdict
from typing import Literal

import pytest
from executing import Source

from ._rewrite_code import ChangeRecorder
from ._rewrite_code import end_of
from ._rewrite_code import start_of

# sentinels
missing_value = object()
undefined = missing_value

snapshots = {}

_active = False

_update_reasons: set[Literal["fix", "recreate", "new", "fit"]] = set()


def ignore_current_value():
    return "fix" in _update_reasons or "recreate" in _update_reasons


@contextlib.contextmanager
def snapshots_disabled():
    with snapshots_env():
        yield


@contextlib.contextmanager
def snapshots_env(*, update_reasons=set(), active=True):
    global snapshots
    global _update_reasons
    global _active

    current = snapshots, _update_reasons, _active

    snapshots = {}
    _update_reasons = update_reasons
    _active = active

    yield

    snapshots, _update_reasons, _active = current


def fix_snapshots(reasons):
    for snapshot in snapshots.values():
        if snapshot._reason in reasons or "all" in reasons:
            snapshot._change()


def snapshot_stat():
    stat = defaultdict(int)
    for snapshot in snapshots.values():
        stat[snapshot._reason] += 1

    return stat


class GenericValue:
    """generic basic implementation for <= >= =="""

    def __init__(self, _old_value):
        self._old_value = _old_value

        if ignore_current_value():
            self._value = undefined
        else:
            self._value = _old_value

    def get_result(self):
        return self._value


class Value(GenericValue):
    def _requires(self):
        return {}

    def _change(self, cls):
        self.__class__ = cls

    def __eq__(self, other):
        self._change(FixValue)
        return self == other

    def __le__(self, other):
        pytest.skip("todo")
        self._change(MinValue)
        return self <= other

    def __ge__(self, other):
        pytest.skip("todo")
        self._change(MaxValue)
        return self >= other

    def __contains__(self, other):
        pytest.skip("todo")
        self._change(CollectionValue)
        return self in other

    def __getitem__(self, item):
        pytest.skip("todo")
        self._change(DictValue)
        return self[item]


class FixValue(GenericValue):
    def __eq__(self, o):
        if self._value is undefined:
            self._value = o
            return True
        else:
            return self._value == o

    def _requires(self):
        if self._old_value is undefined:
            return {"new"}

        if self._old_value != self._value:
            return {"fix"}

        return {}


class MinValue(GenericValue):
    def next_value(self, value):
        self.value = min(value, self.value)
        return True

    def check_result(self, old_value):
        if type(self.value) is not type(old_value):
            return "failing"

        if not self.value <= old_value:
            return "fit"

        if not old_value <= self.value:
            return "failing"

        return "equal"


class MaxValue(GenericValue):
    def next_value(self, value):
        self.value = max(value, self.value)
        return True

    def check_result(self, old_value):
        if type(self.value) is not type(old_value):
            return "failing"

        if not self.value <= old_value:
            return "failing"

        if not old_value <= self.value:
            return "fit"

        return "equal"


class CollectionValue:
    @classmethod
    def new_value(cls, value):
        o = cls()
        o.value = [value]
        return o, True

    def next_value(self, value):
        if value not in self.value:
            self.value.append(value)
        return True

    def get_result(self):
        return self.value

    def check_result(self, old_value):
        if type(old_value) is not list:
            return "failing"
        if any(e not in old_value for e in self.value):
            return "failing"
        if any(e not in self.value for e in old_value):
            return "fit"
        return "equal"


def reduce_result(results):
    results = list(results)
    for result in ("failing", "fit", "equal"):
        if result in results:
            return result
    assert False, results


class DictValue:
    def __init__(self):
        self.value = {}

    @classmethod
    def new_value(cls, key):
        o = cls()
        v = Value()
        o.value[key] = v
        return o, v

    def next_value(self, key):
        if key in self.value:
            return self.value[key]
        else:
            v = Value()
            self.value[key] = v
            return v

    def get_result(self):
        return {k: v.get_result() for k, v in self.value.items()}

    def check_result(self, old_value):
        if type(old_value) is not dict:
            return "failing"

        for key in self.value:
            if key not in old_value:
                return "failing"

        for key in old_value:
            if key not in self.value:
                return "fit"

        return reduce_result(
            self.value[k].check_result(old_value[k]) for k in self.value
        )


def snapshot(obj=missing_value):

    if not _active:
        if obj is missing_value:
            raise AssertionError(
                "your snapshot is missing a value run pytest with --inline-snapshot-create"
            )
        else:
            return obj

    if "new" not in _update_reasons and obj is missing_value:
        raise AssertionError(
            "your snapshot is missing a value run pytest with --inline-snapshot-create"
        )

    frame = inspect.currentframe().f_back
    expr = Source.executing(frame)

    key = expr.node
    key = id(frame.f_code), frame.f_lasti

    if key not in snapshots:
        node = expr.node
        if node is None:
            # we can run without knowing of the calling expression but we will not be able to fix code
            snapshots[key] = Snapshot(obj, None)
        else:
            assert isinstance(node.func, ast.Name)
            assert node.func.id == "snapshot"
            snapshots[key] = Snapshot(obj, expr)

    return snapshots[key]._value


class Snapshot:
    def __init__(self, value, expr):

        self._expr = expr
        self._value = Value(value)

    def __repr__(self):
        return repr(self._value.get_result())

    def _change(self):
        assert self._expr is not None

        change = ChangeRecorder.current.new_change()

        tokens = list(self._expr.source.asttokens().get_tokens(self._expr.node))
        assert tokens[0].string == "snapshot"
        assert tokens[1].string == "("
        assert tokens[-1].string == ")"

        change.set_tags("inline_snapshot", *sorted(self._reason))

        change.replace(
            (end_of(tokens[1]), start_of(tokens[-1])),
            repr(self._value.get_result()),
            filename=self._expr.source.filename,
        )

    @property
    def _reason(self):

        return self._value._requires()
