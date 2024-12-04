from types import SimpleNamespace

from click.testing import CliRunner
from inline_snapshot import snapshot
from inline_snapshot.testing import Example


def test_black_formatting_error(mocker):
    mocker.patch.object(CliRunner, "invoke", return_value=SimpleNamespace(exit_code=1))

    Example(
        """\
from inline_snapshot import snapshot

def test_something():
    assert 1==snapshot()
    assert 1==snapshot(2)
    assert list(range(20)) == snapshot()
"""
    ).run_inline(
        ["--inline-snapshot=fix,create"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from inline_snapshot import snapshot

def test_something():
    assert 1==snapshot(1)
    assert 1==snapshot(1)
    assert list(range(20)) == snapshot([0 ,1 ,2 ,3 ,4 ,5 ,6 ,7 ,8 ,9 ,10 ,11 ,12 ,13 ,14 ,15 ,16 ,17 ,18 ,19 ])
"""
            }
        ),
        report=snapshot(
            """\
─────────────────────────────────── Problems ───────────────────────────────────
black could not format your code, which might be caused by this issue:
    https://github.com/15r10nk/inline-snapshot/issues/138
"""
        ),
    )
