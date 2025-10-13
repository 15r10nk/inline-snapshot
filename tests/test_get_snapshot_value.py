import pytest

from inline_snapshot import Is
from inline_snapshot import external
from inline_snapshot import get_snapshot_value
from inline_snapshot import outsource
from inline_snapshot import snapshot
from inline_snapshot._global_state import snapshot_env
from inline_snapshot._global_state import state


def inspect(value):
    if isinstance(value, (int, str, bytes)):
        return repr(value)

    if isinstance(value, list):
        return "[" + ", ".join(map(inspect, value)) + "]"

    args = ", ".join(f"{k}={v}" for k, v in value.__dict__.items())
    return f"{type(value).__name__}({args})"


@pytest.fixture(params=[True, False])
def try_snapshot_disable(request):
    if request.param != state().active:
        storages = state().all_storages
        with snapshot_env() as env:
            env.active = request.param
            env.all_storages = storages
            yield
    else:
        yield


def test_snapshot(try_snapshot_disable):
    s = snapshot(5)

    assert s == 5

    assert inspect(get_snapshot_value(s)) == snapshot("5")


def test_snapshot_external(try_snapshot_disable):
    s = snapshot([0, external("hash:ef2d127de37b*.json")])

    assert s == [0, 5]

    assert inspect(get_snapshot_value(s)) == snapshot("[0, 5]")


def test_external(try_snapshot_disable):
    s = external("hash:ef2d127de37b*.json")

    assert s == 5

    assert inspect(get_snapshot_value(s)) == snapshot("5")


def test_snapshot_is(try_snapshot_disable):
    s = snapshot([0, Is(5)])

    assert s == [0, 5]

    assert inspect(get_snapshot_value(s)) == snapshot("[0, 5]")


def test_snapshot_snapshot(try_snapshot_disable):
    s = snapshot([0, snapshot(5)])

    assert s == [0, 5]

    assert inspect(get_snapshot_value(s)) == snapshot("[0, 5]")


from dataclasses import dataclass


@dataclass
class A:
    a: int
    b: int


def test_dataclass(try_snapshot_disable):
    s = snapshot(A(a=external("hash:ef2d127de37b*.json"), b=2))

    assert s == A(a=outsource(5), b=2)

    assert inspect(get_snapshot_value(s)) == snapshot("A(a=5, b=2)")
