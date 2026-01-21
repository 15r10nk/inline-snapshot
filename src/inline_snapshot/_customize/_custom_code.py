from __future__ import annotations

import ast
import importlib
from dataclasses import dataclass
from typing import Generator

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._change import ChangeBase
from inline_snapshot._change import RequiredImport
from inline_snapshot._code_repr import HasRepr
from inline_snapshot._code_repr import value_code_repr
from inline_snapshot._utils import clone

from ._custom import Custom


@dataclass(frozen=True)
class Import:
    """Represents an import statement: `import module`"""

    module: str


@dataclass(frozen=True)
class ImportFrom:
    """Represents a from-import statement: `from module import name`"""

    module: str
    name: str


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
    _imports: list[Import | ImportFrom]

    def __init__(self, value, repr_str=None, imports: list[Import | ImportFrom] = []):
        assert not isinstance(value, Custom)
        value = clone(value)
        self._imports = list(imports)

        if repr_str is None:
            self.repr_str = value_code_repr(value)

            try:
                ast.parse(self.repr_str)
            except SyntaxError:
                self.repr_str = HasRepr(type(value), self.repr_str).__repr__()
                self._imports.append(ImportFrom("inline_snapshot", "HasRepr"))
        else:
            self.repr_str = repr_str

        self.value = value

        super().__init__()

    def _map(self, f):
        return f(self.value)

    def _code_repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        for imp in self._imports:
            if isinstance(imp, Import):
                yield RequiredImport(flag="fix", file=context.file, module=imp.module)
            elif isinstance(imp, ImportFrom):
                yield RequiredImport(
                    flag="fix",
                    file=context.file,
                    module=_simplify_module_path(imp.module, imp.name),
                    name=imp.name,
                )
            else:
                assert False

        return self.repr_str

    def __repr__(self):
        return f"CustomValue({self.repr_str})"
