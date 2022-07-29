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

        if reason == "failing":
            with snapshots_disabled():
                with pytest.raises(AssertionError):
                    exec(compile(filename.read_text(), filename, "exec"))

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
                finally:
                    _inline_snapshot._active = False

                for snapshot in _inline_snapshot.snapshots.values():
                    snapshot._change()

                changes = recorder.changes()

                assert len(changes) == 1
                assert changes[0]._tags == ("inline_snapshot", reason)

                recorder.fix_all(tags=["inline_snapshot", reason])

        return filename.read_text()[len(prefix) :]

    return w


def test_comparison(check_update):

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
        reason="equal",
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


def test_le(check_update):

    assert check_update(
        "assert 5<=snapshot()",
        reason="new",
    ) == snapshot("assert 5<=snapshot(5)")

    assert check_update(
        "assert 5<=snapshot(9)",
        reason="shrink",
    ) == snapshot("assert 5<=snapshot(5)")

    assert check_update(
        "assert 5<=snapshot(3)",
        reason="failing",
    ) == snapshot("assert 5<=snapshot(5)")

    assert check_update(
        "assert snapshot(3) >= 5",
        reason="failing",
    ) == snapshot("assert snapshot(5) >= 5")

    assert check_update(
        "assert 5<=snapshot(5)",
        reason="equal",
    ) == snapshot("assert 5<=snapshot(5)")

    assert check_update(
        "for i in range(5): assert i <=snapshot(2)",
        reason="failing",
    ) == snapshot("for i in range(5): assert i <=snapshot(4)")

    assert check_update(
        "for i in range(5): assert i <=snapshot(10)",
        reason="shrink",
    ) == snapshot("for i in range(5): assert i <=snapshot(4)")


def test_le(check_update):

    assert check_update(
        "assert 5>=snapshot()",
        reason="new",
    ) == snapshot("assert 5>=snapshot(5)")

    assert check_update(
        "assert 5>=snapshot(2)",
        reason="shrink",
    ) == snapshot("assert 5>=snapshot(5)")

    assert check_update(
        "assert 5>=snapshot(8)",
        reason="failing",
    ) == snapshot("assert 5>=snapshot(5)")

    assert check_update(
        "assert snapshot(8) <= 5",
        reason="failing",
    ) == snapshot("assert snapshot(5) <= 5")

    assert check_update(
        "assert 5>=snapshot(5)",
        reason="equal",
    ) == snapshot("assert 5>=snapshot(5)")

    assert check_update(
        "for i in range(5): assert i >=snapshot(2)",
        reason="failing",
    ) == snapshot("for i in range(5): assert i >=snapshot(0)")

    assert check_update(
        "for i in range(5): assert i >=snapshot(-10)",
        reason="shrink",
    ) == snapshot("for i in range(5): assert i >=snapshot(0)")


def test_contains(check_update):

    assert check_update(
        "assert 5 in snapshot()",
        reason="new",
    ) == snapshot("assert 5 in snapshot([5])")

    assert check_update(
        "assert 5 in snapshot([])",
        reason="failing",
    ) == snapshot("assert 5 in snapshot([5])")

    assert check_update(
        "assert 5 in snapshot([2])",
        reason="failing",
    ) == snapshot("assert 5 in snapshot([5])")

    assert check_update(
        "assert 5 in snapshot([2,5])",
        reason="shrink",
    ) == snapshot("assert 5 in snapshot([5])")

    assert check_update(
        "for i in range(5): assert i in snapshot([0,1,2,3,4,5,6])",
        reason="shrink",
    ) == snapshot("for i in range(5): assert i in snapshot([0, 1, 2, 3, 4])")


def test_getitem(check_update):

    assert check_update(
        "assert 5 == snapshot()['test']",
        reason="new",
    ) == snapshot("assert 5 == snapshot({'test': 5})['test']")

    assert check_update(
        "for i in range(3): assert i in snapshot()[str(i)]",
        reason="new",
    ) == snapshot(
        "for i in range(3): assert i in snapshot({'0': [0], '1': [1], '2': [2]})[str(i)]"
    )

    assert check_update(
        "for i in range(3): assert i in snapshot({'0': [0], '1': [1], '2': [2]})[str(i)]",
        reason="equal",
    ) == snapshot(
        "for i in range(3): assert i in snapshot({'0': [0], '1': [1], '2': [2]})[str(i)]"
    )

    assert check_update(
        "for i in range(2): assert i in snapshot({'0': [0], '1': [1], '2': [2]})[str(i)]",
        reason="shrink",
    ) == snapshot(
        "for i in range(2): assert i in snapshot({'0': [0], '1': [1]})[str(i)]"
    )

    assert check_update(
        "for i in range(3): assert i in snapshot({'0': [0], '1': [1,2], '2': [4]})[str(i)]",
        reason="failing",
    ) == snapshot(
        "for i in range(3): assert i in snapshot({'0': [0], '1': [1], '2': [2]})[str(i)]"
    )

    assert check_update(
        "for i in range(3): assert i in snapshot({'0': [0], '1': [1,2], '2': [2]})[str(i)]",
        reason="shrink",
    ) == snapshot(
        "for i in range(3): assert i in snapshot({'0': [0], '1': [1], '2': [2]})[str(i)]"
    )
