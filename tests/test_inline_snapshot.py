import textwrap
import traceback

import pytest

from inline_snapshot import _inline_snapshot
from inline_snapshot import snapshot
from inline_snapshot._inline_snapshot import snapshots_disabled
from inline_snapshot._rewrite_code import ChangeRecorder


def test_snapshot_eq():
    with snapshots_disabled():
        assert 1 == snapshot(1)
        assert snapshot(1) == 1


def test_usage_error():
    with snapshots_disabled():
        with pytest.raises(AssertionError):
            for e in (1, 2):
                assert e == snapshot()


def test_assertion_error():
    with snapshots_disabled():
        with pytest.raises(AssertionError):
            for e in (1, 2):
                assert e == snapshot(1)


def test_assertion_error():
    with snapshots_disabled():
        with pytest.raises(AssertionError):
            assert 2 == snapshot(1)


@pytest.fixture()
def check_update(tmp_path):
    filecount = 1

    def w(source, *, reason):
        nonlocal filecount
        filename = tmp_path / f"test_{filecount}.py"
        filecount += 1

        prefix = """
'''
PYTEST_DONT_REWRITE
'''
from inline_snapshot import snapshot
"""

        filename.write_text(prefix + textwrap.dedent(source))

        with snapshots_disabled():
            with ChangeRecorder().activate() as recorder:
                _inline_snapshot._active = True

                try:
                    exec(compile(filename.read_text(), filename, "exec"))
                except AssertionError as error:
                    traceback.print_exc()
                    if reason == "failing":
                        assert str(error) == ""
                    if reason == "new":
                        assert (
                            str(error)
                            == "your snapshot is missing a value run pytest with --update-snapshots=new"
                        )
                else:
                    assert reason != "failing"

                for snapshot in _inline_snapshot.snapshots.values():
                    snapshot._change()

                changes = recorder.changes()

                assert len(changes) == 1
                assert changes[0]._tags == ("inline_snapshot", reason)

                recorder.fix_all(tags=["inline_snapshot", reason])

        return filename.read_text()[len(prefix) :]

    return w


def test_update(check_update):
    assert check_update(
        "assert 5==snapshot()",
        reason="new",
    ) == snapshot("assert 5==snapshot(5)")

    assert check_update(
        "assert 5==snapshot(9)",
        reason="failing",
    ) == snapshot("assert 5==snapshot(5)")

    assert check_update(
        "assert 'a'==snapshot('''a''')",
        reason="force",
    ) == snapshot("assert 'a'==snapshot('a')")

    assert (
        check_update(
            """
            for a in [1,1,1]:
                assert a==snapshot()
            """,
            reason="new",
        )
        == snapshot("\nfor a in [1,1,1]:\n    assert a==snapshot(1)\n")
    )

    assert (
        check_update(
            """
            for a in [1,1,1]:
                assert a==snapshot(2)
            """,
            reason="failing",
        )
        == snapshot("\nfor a in [1,1,1]:\n    assert a==snapshot(1)\n")
    )
