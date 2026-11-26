import ast
import sys

import pytest

from inline_snapshot import snapshot
from inline_snapshot._core._customize._custom_code import CustomCode
from inline_snapshot._core._customize._custom_subscript import CustomSubscript
from inline_snapshot._core._generator_utils import only_value
from inline_snapshot._core._snapshot_context import SnapshotContext
from inline_snapshot.testing import Example


@pytest.mark.parametrize(
    "obj_code, expected",
    [
        ("'a' + 'b'", "('a' + 'b')[1]"),
        ("a or b", "(a or b)[1]"),
        ("a < b", "(a < b)[1]"),
        ("a if condition else b", "(a if condition else b)[1]"),
        ("lambda: a", "(lambda: a)[1]"),
        ("(a := b)", "((a := b))[1]"),
        ("a, b", "(a, b)[1]"),
        ("-a", "(-a)[1]"),
        ("await a", "(await a)[1]"),
        ("(yield a)", "((yield a))[1]"),
        ("(yield from a)", "((yield from a))[1]"),
        ("data", "data[1]"),
        ("data.attr", "data.attr[1]"),
        ("func()", "func()[1]"),
        ("data[0]", "data[0][1]"),
        ("[ 'a',  'b' ]", "[ 'a',  'b' ][1]"),
        ('"ab"', '"ab"[1]'),
        ("{'a': 1}", "{'a': 1}[1]"),
        ("{1, 2}", "{1, 2}[1]"),
        ("[x for x in data]", "[x for x in data][1]"),
        ("(x for x in data)", "(x for x in data)[1]"),
    ],
)
def test_subscript_object_precedence(obj_code, expected):
    value = CustomSubscript(obj=CustomCode(None, obj_code), index=CustomCode(1, "1"))
    code = only_value(value._code_repr(SnapshotContext(sys._getframe())))
    assert code == expected
    intended = ast.Subscript(
        value=ast.parse(obj_code, mode="eval").body,
        slice=ast.Constant(value=1),
        ctx=ast.Load(),
    )
    assert ast.dump(ast.parse(code, mode="eval").body) == ast.dump(intended)


def test_subscript_update_preserves_structure():
    """Test that updating a subscript preserves the subscript structure."""

    Example(
        {
            "conftest.py": """\
from inline_snapshot.plugin import customize

@customize
def handler(value,global_vars,builder):
    for k,v in global_vars.items():
        if isinstance(v,list):
            for i,e in enumerate(v):
                if e == value:
                    return builder.create_subscript(builder.create_code(k),i)
""",
            "tests/test_something.py": """\
from inline_snapshot import snapshot

data = ["a", "b", "c"]

def test_update():
    # Value stays the same, code might need formatting update
    for _ in range(2):
        assert snapshot(data[1]) == "a"
    assert snapshot(data[1]) == "b"
    assert snapshot(data[1]) == "c"
    assert snapshot(data[1]) == "d"
""",
        }
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot({"tests/test_something.py": """\
from inline_snapshot import snapshot

data = ["a", "b", "c"]

def test_update():
    # Value stays the same, code might need formatting update
    for _ in range(2):
        assert snapshot(data[0]) == "a"
    assert snapshot(data[1]) == "b"
    assert snapshot(data[2]) == "c"
    assert snapshot("d") == "d"
"""}),
    )


def test_subscript_create():
    Example(
        {
            "conftest.py": """\
from inline_snapshot.plugin import customize

@customize
def handler(value, builder):
    if value == "b":
        return builder.create_subscript(builder.create_code("data"), 1)
""",
            "tests/test_something.py": """\
from inline_snapshot import snapshot

data = ["a", "b"]

def test_create():
    assert snapshot() == "b"
""",
        }
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files={
            "tests/test_something.py": """\
from inline_snapshot import snapshot

data = ["a", "b"]

def test_create():
    assert snapshot(data[1]) == "b"
""",
        },
    ).run_inline()
