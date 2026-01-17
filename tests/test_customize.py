import pytest

from inline_snapshot import snapshot
from inline_snapshot.testing import Example


@pytest.mark.parametrize(
    "original,flag", [("'a'", "update"), ("'b'", "fix"), ("", "create")]
)
def test_custom_dirty_equal(original, flag):

    Example(
        {
            "tests/conftest.py": """\
from inline_snapshot.plugin import customize
from inline_snapshot.plugin import Builder
from dirty_equals import IsStr

class InlineSnapshotPlugin:
    @customize
    def re_handler(self,value, builder: Builder):
        if value == IsStr(regex="[a-z]"):
            return builder.create_call(IsStr, [], {"regex": "[a-z]"})
""",
            "tests/test_something.py": f"""\
from inline_snapshot import snapshot

def test_a():
    assert snapshot({original}) == "a"
""",
        }
    ).run_inline(
        [f"--inline-snapshot={flag}"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot

from dirty_equals import IsStr

def test_a():
    assert snapshot(IsStr(regex="[a-z]")) == "a"
"""
            }
        ),
    )


@pytest.mark.parametrize(
    "original,flag",
    [("{'1': 1, '2': 2}", "update"), ("5", "fix"), ("", "create")],
)
def test_create_imports(original, flag):

    Example(
        {
            "tests/test_something.py": f"""\
from inline_snapshot import snapshot

def counter():
    from collections import Counter
    return Counter("122")

def test():
    assert counter() == snapshot({original})
"""
        }
    ).run_inline(
        [f"--inline-snapshot={flag}"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot

from collections import Counter

def counter():
    from collections import Counter
    return Counter("122")

def test():
    assert counter() == snapshot(Counter({"1": 1, "2": 2}))
"""
            }
        ),
    )


@pytest.mark.parametrize(
    "original,flag",
    [("ComplexObj(1, 2)", "update"), ("'wrong'", "fix"), ("", "create")],
)
def test_with_import(original, flag):
    """Test that with_import adds both simple and nested module import statements correctly."""

    Example(
        {
            "conftest.py": """\
from inline_snapshot.plugin import customize
from inline_snapshot.plugin import Builder
from pkg.subpkg import ComplexObj

class InlineSnapshotPlugin:
    @customize
    def complex_handler(self, value, builder: Builder):
        if isinstance(value, ComplexObj):
            return builder.create_code(
                value,
                f"mod1.helper(pkg.subpkg.create({value.a!r}, {value.b!r}))"
            ).with_import("mod1").with_import("pkg.subpkg")
""",
            "mod1.py": """\
def helper(obj):
    return obj
""",
            "pkg/__init__.py": "",
            "pkg/subpkg.py": """\
class ComplexObj:
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __eq__(self, other):
        return isinstance(other, ComplexObj) and self.a == other.a and self.b == other.b

def create(a, b):
    return ComplexObj(a, b)
""",
            "test_something.py": f"""\
from inline_snapshot import snapshot
from pkg.subpkg import ComplexObj

def test_a():
    assert snapshot({original}) == ComplexObj(1, 2)
""",
        }
    ).run_inline(
        [f"--inline-snapshot={flag}"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from inline_snapshot import snapshot
from pkg.subpkg import ComplexObj

import mod1
import pkg.subpkg

def test_a():
    assert snapshot(mod1.helper(pkg.subpkg.create(1, 2))) == ComplexObj(1, 2)
"""
            }
        ),
    ).run_inline()


@pytest.mark.parametrize(
    "original,flag", [("MyClass('value')", "update"), ("'wrong'", "fix")]
)
def test_with_import_preserves_existing(original, flag):
    """Test that with_import preserves existing import statements."""

    Example(
        {
            "conftest.py": """\
from inline_snapshot.plugin import customize
from inline_snapshot.plugin import Builder
from mymodule import MyClass

class InlineSnapshotPlugin:
    @customize
    def myclass_handler(self, value, builder: Builder):
        if isinstance(value, MyClass):
            return builder.create_code(
                value,
                f"mymodule.MyClass({value.value!r})"
            ).with_import("mymodule")
""",
            "mymodule.py": """\
class MyClass:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, MyClass) and self.value == other.value
""",
            "test_something.py": f"""\
from inline_snapshot import snapshot
from mymodule import MyClass

import mymodule
import os

def test_a():
    assert snapshot({original}) == MyClass("value")
""",
        }
    ).run_inline(
        [f"--inline-snapshot={flag}"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from inline_snapshot import snapshot
from mymodule import MyClass

import mymodule
import os

def test_a():
    assert snapshot(mymodule.MyClass("value")) == MyClass("value")
"""
            }
        ),
    ).run_inline()
