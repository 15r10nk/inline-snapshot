from inline_snapshot import snapshot
from inline_snapshot.testing import Example


def test_dict_var():

    Example(
        """\
from inline_snapshot import snapshot,Is

def test_list():
    l={1:2}
    assert l == snapshot(l), "not equal"
"""
    ).run_inline(
        ["--inline-snapshot=update"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from inline_snapshot import snapshot,Is

def test_list():
    l={1:2}
    assert l == snapshot({1: 2}), "not equal"
"""
            }
        ),
    )


def test_dict_constructor():

    Example(
        """\
from inline_snapshot import snapshot

def test_dict():
    snapshot(dict())
"""
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot({}),
    )
