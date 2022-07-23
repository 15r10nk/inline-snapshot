import ast
import inspect

from executing import Source

missing_argument = object()


def snapshot(obj=missing_argument):
    return Snapshot(obj)


class UsageError(Exception):
    pass


class Snapshot:
    def __init__(self, obj):
        frame = inspect.currentframe().f_back.f_back
        expr = Source.executing(frame)

        assert isinstance(expr.node.func, ast.Name)
        assert expr.node.func.id == "snapshot"
        self.expr = expr
        self.update_reason = None

        self.obj = obj

    def __eq__(self, o):
        self.new_argument = repr(o)

        if self.obj == missing_argument:
            # so we execute the rest of the code
            self.update_reason = "new"
            return True

        correct = self.obj == o

        if not correct:
            self.update_reason = "failing"

        return self.obj == o
