from inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


def test_namedtuple_default_value():
    # Note: namedtuples with defaults are created using a different approach
    Example(
        """\
from inline_snapshot import snapshot, Is
from collections import namedtuple

A = namedtuple('A', ['a', 'b', 'c'], defaults=[2, []])

def test_something():
    for _ in [1, 2]:
        assert A(a=1) == snapshot(A(a=1, b=2, c=[]))
"""
    ).run_inline(
        ["--inline-snapshot=update"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot, Is
from collections import namedtuple

A = namedtuple('A', ['a', 'b', 'c'], defaults=[2, []])

def test_something():
    for _ in [1, 2]:
        assert A(a=1) == snapshot(A(a=1))
"""
            }
        ),
    )


def test_namedtuple_add_arguments():
    Example(
        """\
from inline_snapshot import snapshot, Is
from collections import namedtuple

A = namedtuple('A', ['a', 'b'], defaults=[2])

def test_something():
    for _ in [1, 2]:
        assert A(a=1, b=5) == snapshot(A(a=1))
"""
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot, Is
from collections import namedtuple

A = namedtuple('A', ['a', 'b'], defaults=[2])

def test_something():
    for _ in [1, 2]:
        assert A(a=1, b=5) == snapshot(A(a=1, b=5))
"""
            }
        ),
    )


def test_namedtuple_positional_arguments():
    Example(
        """\
from inline_snapshot import snapshot, Is
from collections import namedtuple

A = namedtuple('A', ['a', 'b', 'c'], defaults=[2, []])

def test_something():
    for _ in [1, 2]:
        assert A(a=1) == snapshot(A(1, 2, c=[]))
"""
    ).run_inline(
        ["--inline-snapshot=update"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot, Is
from collections import namedtuple

A = namedtuple('A', ['a', 'b', 'c'], defaults=[2, []])

def test_something():
    for _ in [1, 2]:
        assert A(a=1) == snapshot(A(a=1))
"""
            }
        ),
    )


def test_namedtuple_typing():
    Example(
        """\
from inline_snapshot import snapshot
from typing import NamedTuple

class A(NamedTuple):
    a: int
    b: int

def test_something():
    assert A(a=1, b=2) == snapshot()
"""
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot
from typing import NamedTuple

class A(NamedTuple):
    a: int
    b: int

def test_something():
    assert A(a=1, b=2) == snapshot(A(a=1, b=2))
"""
            }
        ),
    )


def test_namedtuple_typing_defaults():
    Example(
        """\
from inline_snapshot import snapshot
from typing import NamedTuple

class A(NamedTuple):
    a: int
    b: int = 2
    c: list = []

def test_something():
    for _ in [1, 2]:
        assert A(a=1) == snapshot(A(a=1, b=2, c=[]))
"""
    ).run_inline(
        ["--inline-snapshot=update"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot
from typing import NamedTuple

class A(NamedTuple):
    a: int
    b: int = 2
    c: list = []

def test_something():
    for _ in [1, 2]:
        assert A(a=1) == snapshot(A(a=1))
"""
            }
        ),
    )


def test_namedtuple_nested():
    Example(
        """\
from inline_snapshot import snapshot
from collections import namedtuple

Inner = namedtuple('Inner', ['x', 'y'])
Outer = namedtuple('Outer', ['a', 'inner'])

def test_something():
    assert Outer(a=1, inner=Inner(x=2, y=3)) == snapshot()
"""
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot
from collections import namedtuple

Inner = namedtuple('Inner', ['x', 'y'])
Outer = namedtuple('Outer', ['a', 'inner'])

def test_something():
    assert Outer(a=1, inner=Inner(x=2, y=3)) == snapshot(Outer(a=1, inner=Inner(x=2, y=3)))
"""
            }
        ),
    )


def test_namedtuple_mixed_args():
    # Test mixing positional and keyword arguments
    Example(
        """\
from inline_snapshot import snapshot
from collections import namedtuple

A = namedtuple('A', ['a', 'b', 'c'])

def test_something():
    assert A(1, b=2, c=3) == snapshot()
"""
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot
from collections import namedtuple

A = namedtuple('A', ['a', 'b', 'c'])

def test_something():
    assert A(1, b=2, c=3) == snapshot(A(a=1, b=2, c=3))
"""
            }
        ),
    )
