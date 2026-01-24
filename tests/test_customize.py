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
from inline_snapshot.plugin import Builder, Import
from pkg.subpkg import ComplexObj

class InlineSnapshotPlugin:
    @customize
    def complex_handler(self, value, builder: Builder):
        if isinstance(value, ComplexObj):
            return builder.create_code(
                f"mod1.helper(pkg.subpkg.create({value.a!r}, {value.b!r}))",
                imports=[Import("mod1"), Import("pkg.subpkg")]
            )
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
@pytest.mark.parametrize("existing_import", ["\nimport mymodule\n", ""])
def test_with_import_preserves_existing(original, flag, existing_import):
    """Test that with_import preserves existing import statements."""

    Example(
        {
            "conftest.py": """\
from inline_snapshot.plugin import customize
from inline_snapshot.plugin import Builder, Import
from mymodule import MyClass

class InlineSnapshotPlugin:
    @customize
    def myclass_handler(self, value, builder: Builder):
        if isinstance(value, MyClass):
            return builder.create_code(
                f"mymodule.MyClass({value.value!r})",
                imports=[Import("mymodule")]
            )
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

import os # just another import
{existing_import}\

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

import os # just another import

import mymodule

def test_a():
    assert snapshot(mymodule.MyClass("value")) == MyClass("value")
"""
            }
        ),
    ).run_inline()


def test_customized_value_mismatch_error():
    """Test that UsageError is raised when customized value doesn't match original."""

    Example(
        {
            "conftest.py": """\
from inline_snapshot.plugin import customize
from inline_snapshot.plugin import Builder

class InlineSnapshotPlugin:
    @customize
    def bad_handler(self, value, builder: Builder):
        if value == 42:
            # Return a CustomCode with wrong value - repr evaluates to 100 but original is 42
            return builder.create_code("100")
""",
            "test_something.py": """\
from inline_snapshot import snapshot

def test_a():
    assert snapshot() == 42
""",
        }
    ).run_inline(
        ["--inline-snapshot=create"],
        raises=snapshot(
            """\
UsageError:
Customized value does not match original value:

original_value=42

customized_value=100
customized_representation=CustomCode('100')
"""
        ),
    )


@pytest.mark.parametrize("original,flag", [("'wrong'", "fix"), ("", "create")])
def test_global_var_lookup(original, flag):
    """Test that create_code can look up global variables."""

    Example(
        {
            "conftest.py": """\
from inline_snapshot.plugin import customize
from inline_snapshot.plugin import Builder

class InlineSnapshotPlugin:
    @customize
    def use_global(self, value, builder: Builder):
        if value == "test_value":
            return builder.create_code("GLOBAL_VAR")
""",
            "test_something.py": f"""\
from inline_snapshot import snapshot

GLOBAL_VAR = "test_value"

def test_a():
    assert snapshot({original}) == "test_value"
""",
        }
    ).run_inline(
        [f"--inline-snapshot={flag}"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from inline_snapshot import snapshot

GLOBAL_VAR = "test_value"

def test_a():
    assert snapshot(GLOBAL_VAR) == "test_value"
"""
            }
        ),
    )


@pytest.mark.parametrize("original,flag", [("'wrong'", "fix"), ("", "create")])
def test_file_handler(original, flag):
    """Test that __file__ handler creates correct code."""

    Example(
        {
            "test_something.py": f"""\
from inline_snapshot import snapshot

def test_a():
    assert snapshot({original}) == __file__
""",
        }
    ).run_inline(
        [f"--inline-snapshot={flag}"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from inline_snapshot import snapshot

def test_a():
    assert snapshot(__file__) == __file__
"""
            }
        ),
    )
