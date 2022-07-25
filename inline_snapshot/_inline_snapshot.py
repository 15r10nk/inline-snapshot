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

# TODO: optimize later
_force_replace = True

_ignore_value = False
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


def snapshot(obj=missing_value):

    if not _active:
        if obj is missing_value:
            raise AssertionError(
                "your snapshot is missing a value run pytest with --update-snapshots=new"
            )
        else:
            return obj

    global _snapshot_id

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
        self._new_value = undefined

        self._current_value = value
        self._reason = None

    def __repr__(self):
        if self._current_value is not missing_value:
            return repr(self._current_value)
        else:
            return repr(self._new_value)

    def _set_argument(self, o, reason):
        if o == self._new_value:
            return
        self._reason = reason
        self._new_value = o

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
            repr(self._new_value),
            filename=self._expr.source.filename,
        )

    def __eq__(self, o):

        if self._current_value == missing_value:
            # x==snapshot()
            # assert "foo" == snapshot()
            # always true because we want to execute the rest of the code
            if self._new_value is undefined:
                # first call
                self._set_argument(o, "new")
                return True
            else:
                # second call
                return o == self._new_value

        correct = self._current_value == o

        if not correct:
            self._set_argument(o, "failing")
        else:
            if _force_replace:
                self._set_argument(o, "force")

        if _ignore_value:
            return True

        return self._current_value == o
