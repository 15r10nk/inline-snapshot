import inspect
from ast import unparse

from executing import Source


class Is:
    def __init__(self, value):
        self.frame = inspect.currentframe().f_back
        ex = Source.executing(self.frame)
        self.ast = ex.node

        self.value = value

    def current_value(self):
        if self.ast is not None:
            return eval(unparse(self.ast), self.frame.f_globals, self.frame.f_locals)
        else:
            return self.value

    def __eq__(self, other):
        return self.current_value() == other

    def __repr__(self):
        return f"Is({repr(self.value)})"
