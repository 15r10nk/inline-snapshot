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
    """
    Custom objects are returned by the `create_*` functions of the builder.
    They should only be returned in your customize function or used as arguments for other `create_*` functions.
    """

    node_type: type[ast.AST] = ast.AST
    original_value: Any

    def __hash__(self):
        return hash(self.eval())

    def __eq__(self, other):
        assert isinstance(other, Custom)
        return self.eval() == other.eval()

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
