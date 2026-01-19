from inline_snapshot import snapshot
from inline_snapshot.extra import raises


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

    with raises(snapshot("SystemExit: 1")):
        exit(1)

    with raises(snapshot("KeyboardInterrupt: ")):
        raise KeyboardInterrupt
