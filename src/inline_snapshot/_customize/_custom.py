from __future__ import annotations

import ast
from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Any
from typing import Generator

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._change import ChangeBase

if TYPE_CHECKING:
    pass


class Custom(ABC):
    node_type: type[ast.AST] = ast.AST
    original_value: Any

    def __hash__(self):
        return hash(self.eval())

    def __eq__(self, other):
        if isinstance(other, Custom):
            other = other.eval()
        return self.eval() == other

    @abstractmethod
    def map(self, f):
        raise NotImplementedError()

    @abstractmethod
    def repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        raise NotImplementedError()

    def eval(self):
        return self.map(lambda a: a)

    def _needed_imports(self):
        yield from ()
