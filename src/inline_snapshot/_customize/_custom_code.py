from __future__ import annotations

import ast
import importlib
from typing import Generator

from typing_extensions import Self

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._change import ChangeBase
from inline_snapshot._change import RequiredImports
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
    _imports: list[tuple[str, str]]
    _module_imports: list[str]

    def __init__(self, value, repr_str=None):
        assert not isinstance(value, Custom)
        value = clone(value)
        self._imports = []
        self._module_imports = []

        if repr_str is None:
            self.repr_str = value_code_repr(value)

            try:
                ast.parse(self.repr_str)
            except SyntaxError:
                self.repr_str = HasRepr(type(value), self.repr_str).__repr__()
                self.with_import_from("inline_snapshot", "HasRepr")
        else:
            self.repr_str = repr_str

        self.value = value

        super().__init__()

    def _map(self, f):
        return f(self.value)

    def _code_repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        file = context.file if context else None

        for module in self._module_imports:
            yield RequiredImports(
                flag="fix", file=file, imports={}, module_imports=[module]
            )
        for module, name in self._imports:
            yield RequiredImports(
                flag="fix", file=file, imports={module: {name}}, module_imports=[]
            )

        return self.repr_str

    def __repr__(self):
        return f"CustomValue({self.repr_str})"

    def with_import_from(self, module: str, name: str, simplify: bool = True) -> Self:
        """
        Adds a `from module import name` statement to the generated code.

        Arguments:
            module: The module path to import from (e.g., "my_module" or "package.submodule").
            name: The name to import from the module (e.g., "MyClass" or "my_function").
            simplify: If True (default), attempts to find the shortest valid import path
                     by checking parent modules. For example, if "package.submodule.MyClass"
                     is accessible from "package", it will use the shorter path.

        Returns:
            The CustomCode instance itself, allowing for method chaining.

        Example:
            ``` python
            builder.create_code(my_obj, "secrets[0]").with_import_from(
                "my_secrets", "secrets"
            )
            ```
        """
        name = name.split("[")[0]
        if simplify:
            module = _simplify_module_path(module, name)
        self._imports.append([module, name])

        return self

    def with_import(self, module: str) -> Self:
        """
        Adds an `import module` statement to the generated code.

        Arguments:
            module: The module path to import (e.g., "os.path" or "collections.abc").

        Returns:
            The CustomCode instance itself, allowing for method chaining.

        Example:
            ``` python
            builder.create_code(my_obj, "os.path.join('a', 'b')").with_import("os.path")
            ```
        """
        self._module_imports.append(module)

        return self
