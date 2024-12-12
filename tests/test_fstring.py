from inline_snapshot import snapshot
from inline_snapshot.extra import warns
from inline_snapshot.testing import Example


def test_fstring():
    Example(
        """
from inline_snapshot import snapshot

def test_a():
    assert "a 1" == snapshot(f"a {1}")
    """
    ).run_inline(reported_categories=snapshot([]))


def test_fstring_fix():

    with warns(
        snapshot(
            [
                """\
InlineSnapshotInfo: inline-snapshot will be able to fix f-strings in the future.
The current string value is:
   'a 1'\
"""
            ]
        )
    ):
        Example(
            """
from inline_snapshot import snapshot

def test_a():
    assert "a 1" == snapshot(f"b {1}"), "not equal"
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
