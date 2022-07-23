import textwrap
import traceback

import pytest

from inline_snapshot import snapshot
from inline_snapshot import UsageError
from inline_snapshot._rewrite_code import ChangeRecorder


def test_snapshot_eq():
    assert 1 == snapshot(1)
    assert snapshot(1) == 1


def test_usage_error():
    with pytest.raises(UsageError):
        for e in (1, 2):
            print(e == snapshot())


def test_assertion_error():
    with pytest.raises(AssertionError):
        for e in (1, 2):
            assert e == snapshot(1)


@pytest.fixture()
def check_update(tmp_path):
    filecount = 1

    def w(source, *, reason):
        nonlocal filecount
        filename = tmp_path / f"test_{filecount}.py"
        filecount += 1

        filename.write_text(
            "from inline_snapshot import snapshot\n" + textwrap.dedent(source)
        )

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

    return w


def test_update(check_update):

    check_update(
        "assert 5==snapshot()",
        reason="new",
    )

    check_update(
        "assert 5==snapshot(9)",
        reason="failing",
    )

    check_update(
        "assert 'a'==snapshot('''a''')",
        reason="force",
    )

    check_update(
        """
        for a in [1,1,1]:
            assert a==snapshot()
        """,
        reason="new",
    )

    check_update(
        """
        for a in [1,1,1]:
            assert a==snapshot(2)
        """,
        reason="failing",
    )
