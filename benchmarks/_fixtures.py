"""Build real source files with distinct snapshot call sites outside timing.

Bump SUITE_VERSION whenever fixtures or timing boundaries change: ASV cannot
hash imported helpers.
"""

import ast
import importlib.util
import sys

from ._workloads import comparison_template
from ._workloads import session_template

SUITE_VERSION = "2"
BATCH_SIZE = 10
CASES = [
    "scalar",
    "text",
    "schema",
    "schema_large",
    "spans",
    "matchers",
    "events",
    "errors",
]


def expand_call_sites(source, count):
    """Repeat the template's test function, preserving literal source syntax.

    A loop calling one function would reuse a single snapshot call site.
    """
    function = next(
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name == "test_snapshot"
    )
    lines = source.splitlines(keepends=True)
    start, end = function.lineno - 1, function.end_lineno
    body = "".join(lines[start + 1 : end])
    functions = [f"def test_snapshot_{i}():\n{body}\n" for i in range(count)]
    return "".join(lines[:start]) + "\n".join(functions) + "".join(lines[end:])


def source(case, *, count=BATCH_SIZE):
    return expand_call_sites(comparison_template(case), count)


def pytest_source(mode, *, count=BATCH_SIZE):
    return expand_call_sites(session_template(mode), count)


def snapshot_functions(module):
    return [getattr(module, f"test_snapshot_{i}") for i in range(BATCH_SIZE)]


def load_module(path):
    name = "_inline_snapshot_benchmark_fixture"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    # Dataclasses inspect sys.modules when resolving annotations.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
