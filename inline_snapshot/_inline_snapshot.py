import ast
import inspect

from executing import Source

# sentinels
missing_argument = object()
undefined = object()

snapshots = {}


class UsageError(Exception):
    pass


def snapshot(obj=missing_argument):
    frame = inspect.currentframe().f_back
    expr = Source.executing(frame)

    node = expr.node
    if node is None:
        return Snapshot(obj, None)

    if node not in snapshots:
        assert isinstance(node.func, ast.Name)
        assert node.func.id == "snapshot"
        snapshots[node] = Snapshot(obj, expr)

    return snapshots[node]


class Snapshot:
    def __init__(self, obj, expr):

        self.expr = expr
        self.update_reason = None
        self.new_argument = undefined

        self.current_argument = obj

    def __eq__(self, o):

        if self.current_argument == missing_argument:
            # x==snapshot()
            self.update_reason = "new"
            # assert "foo" == snapshot()
            # always true because we want to execute the rest of the code
            if self.new_argument is undefined:
                # first call
                self.new_argument = o
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

        self.new_argument = o
        if not correct:
            self.update_reason = "failing"

        return self.current_argument == o
