from dataclasses import dataclass

import pytest

from inline_snapshot import Is
from inline_snapshot import external
from inline_snapshot import get_snapshot_value
from inline_snapshot import outsource
from inline_snapshot import snapshot
from inline_snapshot._global_state import snapshot_env
from inline_snapshot._global_state import state
from inline_snapshot.extra import raises
from inline_snapshot.testing._example import Example


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


def test_external():

    Example("""\
from inline_snapshot import external,snapshot,get_snapshot_value

def inspect(v):
    return f"{type(v).__name__}: {v!r}"

def test_external():
    s = external()

    assert inspect(get_snapshot_value(s,"new")) == snapshot()
    assert inspect(get_snapshot_value(s,"old")) == snapshot()

    assert s == "5"

    assert inspect(get_snapshot_value(s,"new")) == snapshot()
    assert inspect(get_snapshot_value(s,"old")) == snapshot()
""").run_inline(
        ["--inline-snapshot=create"],
        changed_files={
            "tests/__inline_snapshot__/test_something/test_external/e3e70682-c209-4cac-a29f-6fbed82c07cd.txt": "5",
            "tests/test_something.py": """\
from inline_snapshot import external,snapshot,get_snapshot_value

def inspect(v):
    return f"{type(v).__name__}: {v!r}"

def test_external():
    s = external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.txt")

    assert inspect(get_snapshot_value(s,"new")) == snapshot("ellipsis: Ellipsis")
    assert inspect(get_snapshot_value(s,"old")) == snapshot("ellipsis: Ellipsis")

    assert s == "5"

    assert inspect(get_snapshot_value(s,"new")) == snapshot("str: '5'")
    assert inspect(get_snapshot_value(s,"old")) == snapshot("ellipsis: Ellipsis")
""",
        },
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files={"tests/test_something.py": """\
from inline_snapshot import external,snapshot,get_snapshot_value

def inspect(v):
    return f"{type(v).__name__}: {v!r}"

def test_external():
    s = external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.txt")

    assert inspect(get_snapshot_value(s,"new")) == snapshot("str: '5'")
    assert inspect(get_snapshot_value(s,"old")) == snapshot("str: '5'")

    assert s == "5"

    assert inspect(get_snapshot_value(s,"new")) == snapshot("str: '5'")
    assert inspect(get_snapshot_value(s,"old")) == snapshot("str: '5'")
"""},
    ).run_inline(
        ["--inline-snapshot=disable"], reported_categories=set()
    )


def test_external_file():

    Example("""\
from inline_snapshot import external_file,snapshot,get_snapshot_value

def inspect(v):
    return f"{type(v).__name__}: {v!r}"

def test_external():
    s = external_file("file.txt")

    assert inspect(get_snapshot_value(s,"new")) == snapshot()
    assert inspect(get_snapshot_value(s,"old")) == snapshot()

    assert s == "5"

    assert inspect(get_snapshot_value(s,"new")) == snapshot()
    assert inspect(get_snapshot_value(s,"old")) == snapshot()
""").run_inline(
        ["--inline-snapshot=create"],
        changed_files={
            "tests/file.txt": "5",
            "tests/test_something.py": """\
from inline_snapshot import external_file,snapshot,get_snapshot_value

def inspect(v):
    return f"{type(v).__name__}: {v!r}"

def test_external():
    s = external_file("file.txt")

    assert inspect(get_snapshot_value(s,"new")) == snapshot("ellipsis: Ellipsis")
    assert inspect(get_snapshot_value(s,"old")) == snapshot("ellipsis: Ellipsis")

    assert s == "5"

    assert inspect(get_snapshot_value(s,"new")) == snapshot("str: '5'")
    assert inspect(get_snapshot_value(s,"old")) == snapshot("ellipsis: Ellipsis")
""",
        },
        reported_categories={"create", "fix"},
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files={"tests/test_something.py": """\
from inline_snapshot import external_file,snapshot,get_snapshot_value

def inspect(v):
    return f"{type(v).__name__}: {v!r}"

def test_external():
    s = external_file("file.txt")

    assert inspect(get_snapshot_value(s,"new")) == snapshot("str: '5'")
    assert inspect(get_snapshot_value(s,"old")) == snapshot("str: '5'")

    assert s == "5"

    assert inspect(get_snapshot_value(s,"new")) == snapshot("str: '5'")
    assert inspect(get_snapshot_value(s,"old")) == snapshot("str: '5'")
"""},
    ).run_inline(
        ["--inline-snapshot=disable"], reported_categories=set()
    )


def test_snapshot_is(try_snapshot_disable):
    s = snapshot([0, Is(5)])

    assert s == [0, 5]

    assert inspect(get_snapshot_value(s)) == snapshot("[0, 5]")


def test_snapshot_snapshot(try_snapshot_disable):
    s = snapshot([0, snapshot(5)])

    assert s == [0, 5]

    assert inspect(get_snapshot_value(s)) == snapshot("[0, 5]")


def test_get_snapshot_value_defined():
    s = snapshot(5)

    assert get_snapshot_value(s, "new") == 5
    assert get_snapshot_value(s, "old") == 5


def test_get_snapshot_value_undefined():
    with snapshot_env():
        s = snapshot()

        assert get_snapshot_value(s, "new") == ...
        assert get_snapshot_value(s, "old") == ...
        assert s == 5

        assert get_snapshot_value(s, "new") == 5
        assert get_snapshot_value(s, "old") == ...


@dataclass
class A:
    a: int
    b: int


def test_dataclass(try_snapshot_disable):
    s = snapshot(A(a=external("hash:ef2d127de37b*.json"), b=2))

    assert s == A(a=outsource(5), b=2)

    assert inspect(get_snapshot_value(s)) == snapshot("A(a=5, b=2)")


def test_error_message():
    s = snapshot(0)
    with raises("UsageError: which must be 'old' or 'new'"):
        get_snapshot_value(s, "wrong")
