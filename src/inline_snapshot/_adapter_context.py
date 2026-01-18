import ast
from dataclasses import dataclass
from typing import Optional

from inline_snapshot._source_file import SourceFile


@dataclass
class FrameContext:
    globals: dict
    locals: dict


@dataclass
class AdapterContext:
    file: SourceFile
    frame: Optional[FrameContext]
    qualname: str

    def eval(self, node):
        assert self.frame is not None

        return eval(
            compile(ast.Expression(node), self.file.filename, "eval"),
            self.frame.globals,
            self.frame.locals,
        )
