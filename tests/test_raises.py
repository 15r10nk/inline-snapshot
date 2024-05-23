from inline_snapshot import snapshot
from inline_snapshot.extras import raises


def test_raises():
    with raises(snapshot("ZeroDivisionError: division by zero")):
        0 / 0

    with raises(snapshot("<no exception>")):
        pass

    with raises(
        snapshot(
            """\
ValueError:
with
two lines\
"""
        )
    ):
        raise ValueError("with\ntwo lines")
