from inline_snapshot.testing._example import Example


def test_multi_threading():

    Example(
        """
from inline_snapshot import snapshot
import pytest

def test_a():
    assert [
        {
            "input": "wrong",
            "loc": (1,),
            "msg": "Input should be a valid tuple",
        }
    ] == snapshot(
        [
            {
                "input": "wrong",
                "loc": (1,),
                "msg": "Input should be a valid tuple",
            }
        ]
    )


class Foo:
    def __repr__(self):
        return "Foo(<)"


def test_b():
    assert repr(Foo()) == "Foo(<)"

    """
    ).run_pytest(["--parallel-threads=2"])
