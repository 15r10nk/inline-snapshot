from inline_snapshot import snapshot
from inline_snapshot.testing import Example


def test_adapter_mismatch():

    Example(
        """\
from inline_snapshot import snapshot


def test_thing():
    assert [1,2] == snapshot({1:2})

    """
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from inline_snapshot import snapshot


def test_thing():
    assert [1,2] == snapshot([1, 2])

    \
"""
            }
        ),
    )
