from inline_snapshot.testing import Example


def test_is_snapshot():
    Example("""\
from inline_snapshot import is_snapshot, snapshot, snapshot_arg


def check_argument(value):
    s = snapshot_arg(value)
    assert is_snapshot(s)
    assert s == 5


def test_snapshot():
    s = snapshot(5)
    assert is_snapshot(s)
    assert s == 5
    assert is_snapshot(s)

    assert is_snapshot(snapshot())

    s = snapshot({"key": 5})["key"]
    assert is_snapshot(s)
    assert s == 5

    check_argument(5)
""").run_inline()


def test_is_snapshot_ordinary_values():
    Example("""\
from inline_snapshot import Is, external, external_file, is_snapshot, outsource


def test_values():
    for value in (None, ..., True, 5, "text", [], {}, object(), Is(5)):
        assert not is_snapshot(value)

    assert not is_snapshot(external())
    assert not is_snapshot(external_file("value.txt"))
    assert not is_snapshot(outsource(5))
""").run_inline()


def test_is_snapshot_disabled():
    Example("""\
from inline_snapshot import is_snapshot, snapshot, snapshot_arg


def check_argument(value):
    s = snapshot_arg(value)
    assert not is_snapshot(s)
    assert s == 5


def test_snapshot():
    s = snapshot(5)
    assert not is_snapshot(s)
    assert s == 5
    assert not is_snapshot(snapshot({"key": 5})["key"])
    check_argument(5)
""").run_inline(["--inline-snapshot=disable"], reported_categories=set())
