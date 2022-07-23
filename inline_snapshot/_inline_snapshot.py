import ast
import contextlib
import inspect
from collections import defaultdict

from executing import Source

from ._rewrite_code import ChangeRecorder
from ._rewrite_code import end_of
from ._rewrite_code import start_of

# sentinels
missing_argument = object()
undefined = object()

snapshots = {}

# TODO: optimize later
_force_replace = True


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


class UsageError(Exception):
    pass


def snapshot(obj=missing_argument):
    frame = inspect.currentframe().f_back
    expr = Source.executing(frame)

    node = expr.node
    if node is None:
        # we can run without knowing of the calling expression but we will not be able to fix code
        return Snapshot(obj, None)

    if node not in snapshots:
        assert isinstance(node.func, ast.Name)
        assert node.func.id == "snapshot"
        snapshots[node] = Snapshot(obj, expr)

    return snapshots[node]


class Snapshot:
    def __init__(self, value, expr):

        self._expr = expr
        self._new_argument = undefined

        self._current_value = value
        self._reason = None

    def __repr__(self):
        return repr(self._current_value)

    def _set_argument(self, o, reason):
        if o == self._new_argument:
            return
        self._reason = reason
        self._new_argument = o

        self._change()

    def _change(self):
        if self._expr is None:
            return
        change = ChangeRecorder.current.new_change()

        tokens = list(self._expr.source.asttokens().get_tokens(self._expr.node))
        assert tokens[0].string == "snapshot"
        assert tokens[1].string == "("
        assert tokens[-1].string == ")"

        change.set_tags("inline_snapshot", self._reason)

        change.replace(
            (end_of(tokens[1]), start_of(tokens[-1])),
            repr(self._new_argument),
            filename=self._expr.source.filename,
        )

    def __eq__(self, o):

        if self._current_value == missing_argument:
            # x==snapshot()
            # assert "foo" == snapshot()
            # always true because we want to execute the rest of the code
            if self._new_argument is undefined:
                # first call
                self._set_argument(o, "new")
                return True
            else:
                # second call
                result = o == self._new_argument
                if not result:
                    raise UsageError(
                        "got different values first: {self._new_argument} second: {o}"
                    )
                return result

        correct = self._current_value == o

        if not correct:
            self._set_argument(o, "failing")
        else:
            if _force_replace:
                self._set_argument(o, "force")

        return self._current_value == o
