import textwrap
import traceback

import pytest

from inline_snapshot import snapshot
from inline_snapshot import UsageError
from inline_snapshot._rewrite_code import ChangeRecorder
from inline_snapshot._rewrite_code import code_change_disabled


def test_snapshot_eq():
    with code_change_disabled():
        assert 1 == snapshot(1)
        assert snapshot(1) == 1


def test_usage_error():
    with code_change_disabled():
        with pytest.raises(UsageError):
            for e in (1, 2):
                print(e == snapshot())


def test_assertion_error():
    with code_change_disabled():
        with pytest.raises(AssertionError):
            for e in (1, 2):
                assert e == snapshot(1)


def test_assertion_error():
    with code_change_disabled():
        with pytest.raises(AssertionError):
            assert 2 == snapshot(1)


@pytest.fixture()
def check_update(tmp_path):
    filecount = 1

    def w(source, *, reason):
        nonlocal filecount
        filename = tmp_path / f"test_{filecount}.py"
        filecount += 1

        prefix = "from inline_snapshot import snapshot\n"

        filename.write_text(prefix + textwrap.dedent(source))

        with ChangeRecorder().activate() as recorder:
            try:
                exec(compile(filename.read_text(), filename, "exec"))
            except:
                traceback.print_exc()
                assert reason == "failing"
            else:
                assert reason != "failing"

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
