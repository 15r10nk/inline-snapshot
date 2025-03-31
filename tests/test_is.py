from inline_snapshot import Is
from inline_snapshot import snapshot
from inline_snapshot.testing import Example


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


def test_is_repr():
    # repr(Is(x)) == repr(x)
    # see #217
    assert "5" == repr(Is(5))
