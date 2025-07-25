import ast
from typing import Set
from typing import Union

from executing import Source

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


def used_externals_in(source: Union[str, ast.Module], check_import=True) -> Set[str]:
    if isinstance(source, str):
        if "external" not in source:
            return set()
        tree = ast.parse(source)
    else:
        tree = source

    if check_import and not contains_import(tree, "inline_snapshot", "external"):
        return set()

    usages = []

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "external"
        ):
            usages.append(node)

    return {
        u.args[0].value
        for u in usages
        if u.args
        and isinstance(u.args[0], ast.Constant)
        and isinstance(u.args[0].value, str)
    }


def ensure_import(filename, imports, recorder: ChangeRecorder):
    source = Source.for_filename(filename)

    change = recorder.new_change()

    tree = source.tree
    token = source.asttokens()

    to_add = []

    for module, names in imports.items():
        for name in names:
            if not contains_import(tree, module, name):
                to_add.append((module, name))

    assert isinstance(tree, ast.Module)

    last_import = None
    for node in tree.body:
        if not isinstance(node, (ast.ImportFrom, ast.Import)):
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

    code = ""
    for module, name in to_add:
        code += f"\nfrom {module} import {name}\n"

    change.insert(position, code, filename=filename)
