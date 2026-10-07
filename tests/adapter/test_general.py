import pytest

from inline_snapshot import Is
from inline_snapshot import snapshot
from inline_snapshot.testing import Example


@pytest.mark.parametrize(
    "value_type, type_name",
    [
        ("int", "int"),
        ("str", "str"),
        ("float", "float"),
        ("complex", "complex"),
        ("bool", "bool"),
        ("bytes", "bytes"),
        ("type(None)", "NoneType"),
        ("type(Ellipsis)", "ellipsis"),
    ],
)
def test_literal_types_cannot_be_declared_unmanaged(value_type, type_name):
    code = f"""\
from inline_snapshot import declare_unmanaged

def test_a():
    declare_unmanaged({value_type})
"""
    Example({"test_a.py": code}).run_inline(
        raises=Is(f"TypeError: {type_name} cannot be declared unmanaged"),
    )


def test_adapter_mismatch():

    Example("""\
from inline_snapshot import snapshot


def test_thing():
    assert [1,2] == snapshot({1:2})

    """).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot({"tests/test_something.py": """\
from inline_snapshot import snapshot


def test_thing():
    assert [1,2] == snapshot([1, 2])

    \
"""}),
    )


def test_reeval():

    Example("""\
from inline_snapshot import snapshot,Is


def test_thing():
    for i in (1,2):
        assert {1:i} == snapshot({1:Is(i)})
        assert [i] == [Is(i)]
        assert (i,) == (Is(i),)
""").run_pytest(["--inline-snapshot=short-report"], report=snapshot(""))


def test_usageerror_unmanaged():

    Example("""\
from inline_snapshot import snapshot,Is


def test_thing():
    assert [Is(5)] == snapshot([6])
""").run_inline(
        ["--inline-snapshot=fix"],
        report=snapshot(""),
        raises=snapshot(
            "UsageError: unmanaged values cannot be compared with snapshots"
        ),
        reported_categories=set(),
    )
