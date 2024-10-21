from inline_snapshot import snapshot
from inline_snapshot.testing._example import Example

from tests.warns import warns


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
from dataclasses import dataclass,field

@dataclass
class A:
    a:int
    b:int=2
    c:int=field(default_factory=list)

def test_something():
    for c in "ab":
        assert A(a=c) == snapshot(A(a=Is(c),b=2,c=[]))
"""
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from inline_snapshot import snapshot,Is
from dataclasses import dataclass,field

@dataclass
class A:
    a:int
    b:int=2
    c:int=field(default_factory=list)

def test_something():
    for c in "ab":
        assert A(a=c) == snapshot(A(a=Is(c)))
"""
            }
        ),
    )


def test_disabled(executing_used):
    Example(
        """\
from inline_snapshot import snapshot
from dataclasses import dataclass

@dataclass
class A:
    a:int

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


def test_starred_warns():
    with warns(
        snapshot(
            [
                (
                    10,
                    "InlineSnapshotSyntaxWarning: star-expressions are not supported inside snapshots",
                )
            ]
        ),
        include_line=True,
    ):
        Example(
            """
from inline_snapshot import snapshot
from dataclasses import dataclass

@dataclass
class A:
    a:int

def test_something():
    assert A(a=3) == snapshot(A(**{"a":5})),"not equal"
"""
        ).run_inline(
            ["--inline-snapshot=fix"],
            raises=snapshot(
                """\
AssertionError:
not equal\
"""
            ),
        )


def test_add_argument():
    Example(
        """\
from inline_snapshot import snapshot
from dataclasses import dataclass

@dataclass
class A:
    a:int=0
    b:int=0
    c:int=0

def test_something():
    assert A(a=3,b=3,c=3) == snapshot(A(b=3)),"not equal"
"""
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from inline_snapshot import snapshot
from dataclasses import dataclass

@dataclass
class A:
    a:int=0
    b:int=0
    c:int=0

def test_something():
    assert A(a=3,b=3,c=3) == snapshot(A(a = 3, b=3, c = 3)),"not equal"
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
