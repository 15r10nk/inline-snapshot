import pytest
from executing import is_pytest_compatible

from inline_snapshot import snapshot
from inline_snapshot.testing import Example


@pytest.mark.skipif(
    is_pytest_compatible(),
    reason="this is only a problem when executing can return None",
)
def test_without_node():

    Example(
        {
            "conftest.py": """\
from inline_snapshot.plugin import customize

@customize
def handler(value,builder):
    if value=="foo":
        return builder.create_code("'foo'")
""",
            "test_example.py": """\
from inline_snapshot import snapshot
from dirty_equals import IsStr

def test_foo():
    assert "not_foo" == snapshot(IsStr())
""",
        }
    ).run_pytest()


def test_custom_default_case_in_ValueToCustom(executing_used):
    Example(
        """\
from inline_snapshot import snapshot
from dataclasses import dataclass

@dataclass
class A:
    a:int=5

def test_something():
    assert A(a=3) == snapshot(A(a=5)),"not equal"
"""
    ).run_inline(
        changed_files=snapshot({}),
        raises=snapshot(
            """\
AssertionError:
not equal\
"""
        ),
    )


def test_tuple_case_in_ValueToCustom(executing_used):
    Example(
        """\
from inline_snapshot import snapshot
from dataclasses import dataclass

@dataclass
class A:
    a:int=5

def test_something():
    assert (1,2) == snapshot((1,2)),"not equal"
"""
    ).run_inline(
        changed_files=snapshot({}),
        raises=snapshot(None),
    )
