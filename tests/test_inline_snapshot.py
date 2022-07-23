import pytest

from inline_snapshot import snapshot
from inline_snapshot import UsageError


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
