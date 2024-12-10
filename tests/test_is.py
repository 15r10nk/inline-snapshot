from inline_snapshot._inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


def test_missing_is():

    Example(
        """\
from inline_snapshot import snapshot

def test_is():
    for i in (1,2):
        assert i == snapshot(i)
    """
    ).run_inline(
        raises=snapshot(
            """\
UsageError:
snapshot value should not change. Use Is(...) for dynamic snapshot parts.\
"""
        )
    )
