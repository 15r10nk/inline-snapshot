from inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


def test_repr():
    Example(
        """\
from inline_snapshot import snapshot
from inline_snapshot.extra import IsTransformed

def test_a():
    n=IsTransformed(sorted,snapshot())
    assert [3,5,2] == n
    assert repr(n) == snapshot()
"""
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from inline_snapshot import snapshot
from inline_snapshot.extra import IsTransformed

def test_a():
    n=IsTransformed(sorted,snapshot([2, 3, 5]))
    assert [3,5,2] == n
    assert repr(n) == snapshot("IsTransformed(sorted,[2, 3, 5])")
"""
            }
        ),
    ).code_change(
        "[3,5,2]", "[3,6,2]"
    ).run_pytest(
        error=snapshot(
            """\
>       assert [3,6,2] == n
E       assert [3, 6, 2] == IsTransformed(sorted, [2, 3, 5], should_be=[2, 3, 6])
"""
        ),
        returncode=1,
    )
