from __future__ import annotations

import ast
import importlib
from typing import Generator

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._change import ChangeBase
from inline_snapshot._code_repr import HasRepr
from inline_snapshot._code_repr import value_code_repr
from inline_snapshot._utils import clone

from ._custom import Custom


def _simplify_module_path(module: str, name: str) -> str:
    """Simplify module path by finding the shortest import path for a given name."""
    value = getattr(importlib.import_module(module), name)
    parts = module.split(".")
    while len(parts) >= 2:
        if getattr(importlib.import_module(".".join(parts[:-1])), name, None) == value:
            parts.pop()
        else:
            break
    return ".".join(parts)


class CustomCode(Custom):
    def __init__(self, value, repr_str=None):
        assert not isinstance(value, Custom)
        value = clone(value)
        self._imports = []

        if repr_str is None:
            self.repr_str = value_code_repr(value)

            try:
                ast.parse(self.repr_str)
            except SyntaxError:
                self.repr_str = HasRepr(type(value), self.repr_str).__repr__()
                self.with_import("inline_snapshot", "HasRepr")
        else:
            self.repr_str = repr_str

        self.value = value

        super().__init__()

    def map(self, f):
        return f(self.value)

    def repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        yield from ()
        return self.repr_str

    def __repr__(self):
        return f"CustomCode({self.repr_str})"

    def _needed_imports(self):
        yield from self._imports

    def with_import(self, module, name, simplify=True):
        if simplify:
            module = _simplify_module_path(module, name)
        self._imports.append([module, name])

        return self
