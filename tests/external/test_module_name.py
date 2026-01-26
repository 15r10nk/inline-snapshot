"""Tests for module_name_of function coverage."""

from inline_snapshot import snapshot
from inline_snapshot.testing import Example


def test_module_name_init_py_with_snapshot():
    """Test module_name_of when __init__.py itself contains the snapshot call."""
    Example(
        {
            "tests/__init__.py": "",
            "tests/mypackage/b.py": """\
from dataclasses import dataclass

@dataclass
class B:
    b:int
""",
            "tests/mypackage/__init__.py": """\
from inline_snapshot import snapshot
from dataclasses import dataclass

@dataclass
class A:
    a:int

s = snapshot()
""",
            "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_a():
    from .mypackage import s,A
    from .mypackage.b import B
    assert s == [A(5),B(5)]
""",
        }
    ).run_pytest(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "tests/mypackage/__init__.py": """\
from inline_snapshot import snapshot
from dataclasses import dataclass

from tests.mypackage.b import B

@dataclass
class A:
    a:int

s = snapshot([A(a=5), B(b=5)])
"""
            }
        ),
        returncode=1,
    ).run_pytest(
        ["--inline-snapshot=disable"]
    )
