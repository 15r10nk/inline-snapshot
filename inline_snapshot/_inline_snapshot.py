import ast
import contextlib
import inspect
from collections import defaultdict

from executing import Source

from ._rewrite_code import ChangeRecorder
from ._rewrite_code import end_of
from ._rewrite_code import start_of

# sentinels
missing_value = object()
undefined = object()

snapshots = {}

_active = False


@contextlib.contextmanager
def snapshots_disabled():
    global snapshots
    current = snapshots
    snapshots = {}
    yield
    snapshots = current


def fix_snapshots(reasons):
    for snapshot in snapshots.values():
        if snapshot._reason in reasons or "all" in reasons:
            snapshot._change()


def snapshot_stat():
    stat = defaultdict(int)
    for snapshot in snapshots.values():
        stat[snapshot._reason] += 1

    return stat


class Value:
    def __init__(self):
        self._value = undefined

    def _process(self, cls, value):

        if self._value is undefined:
            self._value, result = cls.new_value(value)
            return result
        else:
            assert isinstance(self._value, cls), (self._value, cls)
            return self._value.next_value(value)

    def get_result(self):
        return self._value.get_result()

    def check_result(self, old_value):
        return self._value.check_result(old_value)

    def __eq__(self, other):
        return self._process(FixValue, other)

    def __le__(self, other):
        return self._process(MaxValue, other)

    def __ge__(self, other):
        return self._process(MinValue, other)

    def __contains__(self, other):
        return self._process(CollectionValue, other)

    def __getitem__(self, other):
        return self._process(DictValue, other)


class GenericValue:
    """generic basic implementation for <= >= =="""

    @classmethod
    def new_value(cls, value):
        o = cls()
        o.value = value
        return o, True

    def get_result(self):
        return self.value


class FixValue(GenericValue):
    def next_value(self, value):
        return self.value == value

    def check_result(self, old_value):
        print(self.value, old_value)
        if type(self.value) is not type(old_value):
            return "failing"

        if self.value == old_value:
            return "equal"
        else:
            return "failing"


class MinValue(GenericValue):
    def next_value(self, value):
        self.value = min(value, self.value)
        return True

    def check_result(self, old_value):
        if type(self.value) is not type(old_value):
            return "failing"

        if not self.value <= old_value:
            return "shrink"

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
            return "shrink"

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
            return "shrink"
        return "equal"


def reduce_result(results):
    results = list(results)
    for result in ("failing", "shrink", "equal"):
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
                return "shrink"

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

    return snapshots[key]


class Snapshot:
    def __init__(self, value, expr):

        self._expr = expr
        self._new_value = Value()

        self._current_value = value

    def __repr__(self):
        return repr(self._new_value.get_result())

    def _change(self):
        assert self._expr is not None

        change = ChangeRecorder.current.new_change()

        tokens = list(self._expr.source.asttokens().get_tokens(self._expr.node))
        assert tokens[0].string == "snapshot"
        assert tokens[1].string == "("
        assert tokens[-1].string == ")"

        change.set_tags("inline_snapshot", self._reason)

        change.replace(
            (end_of(tokens[1]), start_of(tokens[-1])),
            repr(self._new_value.get_result()),
            filename=self._expr.source.filename,
        )

    @property
    def _reason(self):
        if self._current_value == missing_value:
            return "new"

        return self._new_value.check_result(self._current_value)

    def __eq__(self, other):
        return other == self._new_value

    def __le__(self, other):
        return other <= self._new_value

    def __ge__(self, other):
        return other >= self._new_value

    def __contains__(self, other):
        return other in self._new_value

    def __getitem__(self, other):
        return self._new_value[other]
