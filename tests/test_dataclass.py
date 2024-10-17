from inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


def test_unmanaged():

    Example(
        """
from inline_snapshot import snapshot,Is

def test_something():
    assert {1:2,3:4} == snapshot({1:1,3:Is(1)}), "not equal"

    """
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "test_something.py": """\

from inline_snapshot import snapshot,Is

def test_something():
    assert {1:2,3:4} == snapshot({1:2,3:Is(1)}), "not equal"

    \
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
