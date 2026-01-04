from __future__ import annotations

import ast
from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Any
from typing import Callable
from typing import Generator
from typing import TypeAlias

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._change import ChangeBase

if TYPE_CHECKING:
    from inline_snapshot._customize._builder import Builder


class Custom(ABC):
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


CustomizeHandler: TypeAlias = Callable[[Any, "Builder"], Custom | None]
"""
Type alias for customization handler functions.

A customization handler is a function that takes a Python value and a Builder,
and returns either a Custom representation or None.

The handler receives two parameters:

- `value` (Any): The Python object to be converted to snapshot code
- `builder` (Builder): Helper object providing methods to create Custom representations

The handler should return a Custom object if it processes the value type, or None otherwise.
"""
