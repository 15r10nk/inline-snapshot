from inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


def test_unmanaged():

    Example(
        """\
from inline_snapshot import snapshot,Is
from dataclasses import dataclass

@dataclass
class A:
    a:int
    b:int

def test_something():
    assert A(a=2,b=4) == snapshot(A(a=1,b=Is(1))), "not equal"
"""
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from inline_snapshot import snapshot,Is
from dataclasses import dataclass

@dataclass
class A:
    a:int
    b:int

def test_something():
    assert A(a=2,b=4) == snapshot(A(a=2,b=Is(1))), "not equal"
"""
            }
        ),
        raises=snapshot(
            """\
AssertionError:
not equal\
"""
        ),
    )


def test_reeval():
    Example(
        """\
from inline_snapshot import snapshot,Is
from dataclasses import dataclass

@dataclass
class A:
    a:int
    b:int

def test_something():
    for c in "ab":
        assert A(a=1,b=c) == snapshot(A(a=2,b=Is(c)))
"""
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from inline_snapshot import snapshot,Is
from dataclasses import dataclass

@dataclass
class A:
    a:int
    b:int

def test_something():
    for c in "ab":
        assert A(a=1,b=c) == snapshot(A(a=1,b=Is(c)))
"""
            }
        ),
    )


def test_default_value():
    Example(
        """\
from inline_snapshot import snapshot,Is
from dataclasses import dataclass

@dataclass
class A:
    a:int
    b:int=2

def test_something():
    for c in "ab":
        assert A(a=c,b=2) == snapshot(A(a=Is(c),b=2))
"""
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from inline_snapshot import snapshot,Is
from dataclasses import dataclass

@dataclass
class A:
    a:int
    b:int=2

def test_something():
    for c in "ab":
        assert A(a=c,b=2) == snapshot(A(a=Is(c)))
"""
            }
        ),
    )
