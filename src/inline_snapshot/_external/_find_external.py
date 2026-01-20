import ast
import os
from dataclasses import replace
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Union

from executing import Source

from inline_snapshot._external._external_location import ExternalLocation

from .._rewrite_code import ChangeRecorder
from .._rewrite_code import end_of
from .._rewrite_code import start_of


def contains_import(tree, module, name):
    for node in tree.body:
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == module
            and any(alias.name == name for alias in node.names)
        ):
            return True
    return False


def contains_module_import(tree, module):
    for node in tree.body:
        if isinstance(node, ast.Import):
            if any(
                alias.name == module and alias.asname is None for alias in node.names
            ):
                return True
    return False


def used_externals_in(
    filename: Path, source: Union[str, ast.Module], check_import=True
) -> List[ExternalLocation]:
    if isinstance(source, str):
        if "external" not in source:
            return []
        tree = ast.parse(source)
    else:
        tree = source

    if check_import and not contains_import(tree, "inline_snapshot", "external"):
        return []

    usages = []

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "external"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            arg = node.args[0].value

            try:
                location = replace(
                    ExternalLocation.from_name(arg),
                    filename=filename,
                    linenumber=node.lineno,
                )
            except ValueError:
                pass
            else:
                usages.append(location)

    return usages


def module_name_of(filename: Union[str, os.PathLike]) -> Optional[str]:
    path = Path(filename).resolve()

    assert path.suffix == ".py"

    parts = []

    if path.name != "__init__.py":
        parts.append(path.stem)

    current = path.parent

    while current != current.root:
        if not (current / "__init__.py").exists():
            break

        parts.append(current.name)

        next_parent = current.parent
        if next_parent == current:
            break  # pragma: no cover
        current = next_parent
    else:
        pass  # pragma: no cover

    parts.reverse()

    assert parts

    return ".".join(parts)


def ensure_import(
    filename,
    imports: Dict[str, Set[str]],
    module_imports: Set[str],
    recorder: ChangeRecorder,
):
    print("file", filename)
    source = Source.for_filename(filename)

    change = recorder.new_change()

    tree = source.tree
    token = source.asttokens()

    my_module_name = module_name_of(filename)

    code = ""
    for module, names in imports.items():
        if module == my_module_name:
            continue
        if module == "builtins":
            continue
        for name in sorted(names):
            if not contains_import(tree, module, name):
                code += f"from {module} import {name}\n"

    for module in sorted(module_imports):
        if not contains_module_import(tree, module):
            code += f"import {module}\n"

    assert isinstance(tree, ast.Module)

    # find source position
    last_import = None
    for node in tree.body:
        if not (
            isinstance(node, (ast.ImportFrom, ast.Import))
            or (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            )
        ):
            break
        last_import = node

    if last_import is None:
        position = start_of(tree.body[0].first_token)  # type: ignore
    else:
        last_token = last_import.last_token  # type: ignore
        while True:
            next_token = token.next_token(last_token)
            if last_token.end[0] == next_token.end[0]:
                last_token = next_token
            else:
                break
        position = end_of(last_token)

    if code:
        code = "\n" + code
        change.insert(position, code, filename=filename)
