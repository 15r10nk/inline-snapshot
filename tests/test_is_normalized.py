from inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


def test_repr():
    Example(
        """\
from inline_snapshot import snapshot
from tests._is_normalized import IsNormalized

def test_a():
    n=IsNormalized(sorted,snapshot())
    assert [3,5,2] == n
    assert repr(n)==snapshot()
"""
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from inline_snapshot import snapshot
from tests._is_normalized import IsNormalized

def test_a():
    n=IsNormalized(sorted,snapshot([2, 3, 5]))
    assert [3,5,2] == n
    assert repr(n)==snapshot("IsNormalized([2, 3, 5], should_be=[2, 3, 5])")
"""
            }
        ),
    )
