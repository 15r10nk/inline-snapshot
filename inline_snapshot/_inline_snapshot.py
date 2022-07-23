import ast
import inspect

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

        self.expr = expr
        self.new_argument = undefined

        self.change = ChangeRecorder.current.new_change()

        self.current_argument = value

    def _set_argument(self, o, reason):
        if o == self.new_argument:
            return

        if self.expr is None:
            return

        tokens = list(self.expr.source.asttokens().get_tokens(self.expr.node))
        print(tokens)
        assert tokens[0].string == "snapshot"
        assert tokens[1].string == "("
        assert tokens[-1].string == ")"

        self.change.set_tags("inline_snapshot", reason)

        self.change.replace(
            (end_of(tokens[1]), start_of(tokens[-1])),
            repr(o),
            filename=self.expr.source.filename,
        )

        self.new_argument = o

    def __eq__(self, o):

        if self.current_argument == missing_argument:
            # x==snapshot()
            # assert "foo" == snapshot()
            # always true because we want to execute the rest of the code
            if self.new_argument is undefined:
                # first call
                self._set_argument(o, "new")
                return True
            else:
                # second call
                result = o == self.new_argument
                if not result:
                    raise UsageError(
                        "got different values first: {self.new_argument} second: {o}"
                    )
                return result

        correct = self.current_argument == o

        if not correct:
            self._set_argument(o, "failing")
        else:
            if _force_replace:
                self._set_argument(o, "force")

        return self.current_argument == o
