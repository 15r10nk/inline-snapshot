import ast
import sys
from dataclasses import dataclass
from functools import cached_property
from types import FrameType
from typing import cast

from executing import Source

from inline_snapshot._source_file import SourceFile


@dataclass
class FrameContext:
    globals: dict
    locals: dict


class AdapterContext:

    _frame: FrameType

    def __init__(self, frame: FrameType):
        self._frame = frame

    @cached_property
    def expr(self):
        return Source.executing(self._frame)

    @property
    def source(self) -> Source:
        return cast(
            Source,
            getattr(self.expr, "source", None) if self.expr is not None else None,
        )

    @property
    def file(self):
        return SourceFile(self.source)

    @property
    def frame(self) -> FrameContext:
        return FrameContext(globals=self._frame.f_globals, locals=self._frame.f_locals)

    @cached_property
    def local_vars(self):
        """Get local vars from snapshot context."""
        return {
            var_name: var_value
            for var_name, var_value in self._frame.f_locals.items()
            if "@" not in var_name
        }

    @cached_property
    def global_vars(self):
        """Get global vars from snapshot context."""
        return {
            var_name: var_value
            for var_name, var_value in self._frame.f_globals.items()
            if "@" not in var_name
        }

    @cached_property
    def qualname(self) -> str:
        if sys.version_info >= (3, 11):
            return self._frame.f_code.co_qualname
        else:
            return self.expr.code_qualname()

    def eval(self, node):
        assert self.frame is not None

        return eval(
            compile(ast.Expression(node), self.file.filename, "eval"),
            self.frame.globals,
            self.frame.locals,
        )
