import sys

import pytest

from inline_snapshot import Is
from inline_snapshot import snapshot
from inline_snapshot.testing import Example


@pytest.mark.parametrize(
    "obj_code, expected",
    [
        ("'a' + 'b'", "('a' + 'b')[1]"),
        ("'ab' or 'cd'", "('ab' or 'cd')[1]"),
        ("data < data", "(data < data)[1]"),
        ("'ab' if True else 'cd'", "('ab' if True else 'cd')[1]"),
        ('(a := "ab")', '((a := "ab"))[1]'),
        ("'a', 'b'", "('a', 'b')[1]"),
        ("-data", "(-data)[1]"),
        ("data", "data[1]"),
        ("data.attr", "data.attr[1]"),
        ("func()", "func()[1]"),
        ("data[0]", "data[0][1]"),
        ("[ 'a',  'b' ]", "[ 'a',  'b' ][1]"),
        ('"ab"', '"ab"[1]'),
        ("{1: 'b'}", "{1: 'b'}[1]"),
        ("[x for x in 'ab']", "[x for x in 'ab'][1]"),
    ],
)
def test_subscript_object_precedence(obj_code, expected):
    source = """\
from inline_snapshot import snapshot

class Data:
    attr = "ab"

    def __getitem__(self, index):
        return "ab" if index == 0 else "b"

    def __lt__(self, other):
        return "ab"

    def __neg__(self):
        return "ab"

    def __eq__(self, other):
        return isinstance(other, Data)

data = Data()

def func():
    return "ab"

def test_precedence():
    assert "b" == snapshot()
"""
    Example(
        {
            "conftest.py": f"""\
from inline_snapshot.plugin import customize

@customize
def handler(value, builder):
    if value == "b":
        return builder.create_subscript(builder.create_code({obj_code!r}), 1)
""",
            "tests/test_something.py": source,
            # Keep generated source unchanged so formatting cannot repair precedence
            # or obscure changes to quotes and whitespace.
            "pyproject.toml": f"""\
[tool.inline-snapshot]
format-command = '{sys.executable} format.py'
""",
            "format.py": """\
import sys
# Exercise Windows newline translation on every platform.
sys.stdout.reconfigure(newline="\\r\\n")
sys.stdout.buffer.write(sys.stdin.buffer.read())
""",
        }
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files={
            "tests/test_something.py": Is(
                source.replace("snapshot()", f"snapshot({expected})")
            )
        },
    ).run_inline(
        ["--inline-snapshot=disable"], reported_categories=set()
    )


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


@pytest.mark.parametrize(
    "indices, expected",
    [((), "data[()]"), ((1,), "data[1,]"), ((1, 2), "data[1, 2]")],
)
def test_subscript_tuple_index(indices, expected):
    source = """\
from inline_snapshot import snapshot

data = {(): "b", (1,): "b", (1, 2): "b"}

def test_tuple_index():
    assert "b" == snapshot()
"""
    Example(
        {
            "conftest.py": f"""\
from inline_snapshot.plugin import customize

@customize
def handler(value, builder):
    if value == "b":
        return builder.create_subscript(
            builder.create_code("data"), builder.create_tuple({indices!r})
        )
""",
            "tests/test_something.py": source,
        }
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files={
            "tests/test_something.py": Is(
                source.replace("snapshot()", f"snapshot({expected})")
            )
        },
    ).run_inline(
        changed_files={}
    ).run_inline(
        ["--inline-snapshot=disable"], reported_categories=set()
    )
