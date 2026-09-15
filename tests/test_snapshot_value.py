"""Tests for snapshot_value parameter in customize hooks."""

import pytest
from dirty_equals import AnyThing

from inline_snapshot import snapshot
from inline_snapshot.testing import Example

HEX_IF_EXISTING = """\
from inline_snapshot.plugin import customize

@customize
def hex_if_existing(value, builder, snapshot_value):
    if isinstance(value, int):
        if snapshot_value is not ...:
            return builder.create_code(hex(value))
        return builder.create_code(str(value))
"""


def test_snapshot_value_in_list():
    """Test that snapshot_value works with list elements."""
    Example(
        {
            "tests/conftest.py": """\
from inline_snapshot import snapshot
from inline_snapshot.plugin import customize

old_new_mapping={}

@customize
def double_if_old_exists(value, builder, snapshot_value):
    if isinstance(value,int):
        assert value in (1,2,3,4,5,6,8,0)
        old_new_mapping[value]=snapshot_value
        return builder.create_code(str(value))

""",
            "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_it():
    # When we fix, the runtime value [1, 2, 3, 4, 5, 6] is compared with snapshot [1, 8, 3, 4, 5, 0]
    # Each runtime element should see its corresponding snapshot element:
    # 1 -> 1, 2 -> 8, 3 -> 3, 4 -> 4, 5 -> 5, 6 -> 0
    assert snapshot([1, 8, 3,4,5,0]) == [1, 2, 3,4,5,6]
    from conftest import old_new_mapping

    assert dict(old_new_mapping)==snapshot()
""",
        }
    ).run_pytest(
        ["--inline-snapshot=fix,create"],
        # Runtime [1, 2, 3, 4, 5, 6] compared with snapshot [1, 8, 3, 4, 5, 0]
        # Each runtime value gets the corresponding snapshot value:
        # 1->1, 2->8, 3->3, 4->4, 5->5, 6->0
        returncode=1,  # Expect error due to missing snapshot being created
        changed_files=snapshot({"tests/test_something.py": """\
from inline_snapshot import snapshot

def test_it():
    # When we fix, the runtime value [1, 2, 3, 4, 5, 6] is compared with snapshot [1, 8, 3, 4, 5, 0]
    # Each runtime element should see its corresponding snapshot element:
    # 1 -> 1, 2 -> 8, 3 -> 3, 4 -> 4, 5 -> 5, 6 -> 0
    assert snapshot([1, 2, 3,4,5,6]) == [1, 2, 3,4,5,6]
    from conftest import old_new_mapping

    assert dict(old_new_mapping)==snapshot({1: 1, 2: 8, 3: 3, 4: 4, 5: 5, 6: 0})
"""}),
        outcomes={"passed": 1, "errors": 1},
    )


def test_snapshot_value_undefined():
    Example(
        {
            "tests/conftest.py": """\
from inline_snapshot.plugin import customize

@customize
def check_undefined(value, builder, snapshot_value):
    if isinstance(value, int):
        assert snapshot_value is ...
        return builder.create_code(str(value))
""",
            "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_it():
    assert 5 == snapshot()
""",
        }
    ).run_pytest(
        ["--inline-snapshot=create"],
        changed_files=snapshot({"tests/test_something.py": """\
from inline_snapshot import snapshot

def test_it():
    assert 5 == snapshot(5)
"""}),
        returncode=1,
        outcomes={"passed": 1, "errors": 1},
    )


def test_snapshot_value_list_insert():
    Example(
        {
            "tests/conftest.py": """\
from inline_snapshot.plugin import customize

@customize
def check_list_insert(value, builder, snapshot_value):
    if value == 1:
        assert snapshot_value == 1
        return builder.create_code(str(value))
    if value == 2:
        assert snapshot_value is ...
        return builder.create_code(str(value))
""",
            "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_it():
    assert [1, 2] == snapshot([1])
""",
        }
    ).run_pytest(
        ["--inline-snapshot=fix"],
        changed_files=snapshot({"tests/test_something.py": """\
from inline_snapshot import snapshot

def test_it():
    assert [1, 2] == snapshot([1, 2])
"""}),
        returncode=1,
        outcomes={"passed": 1, "errors": 1},
    )


def test_snapshot_value_new_dict_key():
    Example(
        {
            "tests/conftest.py": """\
from inline_snapshot.plugin import customize

@customize
def check_new_dict_key(value, builder, snapshot_value):
    if value == 1:
        assert snapshot_value == 1
        return builder.create_code(str(value))
    if value == 2:
        assert snapshot_value is ...
        return builder.create_code(str(value))
""",
            "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_it():
    assert {1: "a", 2: "b"} == snapshot({1: "a"})
""",
        }
    ).run_pytest(
        ["--inline-snapshot=fix"],
        changed_files=snapshot({"tests/test_something.py": """\
from inline_snapshot import snapshot

def test_it():
    assert {1: "a", 2: "b"} == snapshot({1: "a", 2: "b"})
"""}),
        returncode=1,
        outcomes={"passed": 1, "errors": 1},
    )


def test_snapshot_value_in_dict_key():
    """Test that snapshot_value works with existing dict keys."""
    Example(
        {
            "tests/conftest.py": """\
from inline_snapshot.plugin import customize

@customize
def check_dict_key(value, builder, snapshot_value):
    if value == 1 and builder._build_new_value:
        assert snapshot_value == 1, repr(snapshot_value)
        return builder.create_code(str(value))

""",
            "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_it():
    assert snapshot({1: "x"}) == {1: "x"}
""",
        }
    ).run_pytest()


def test_snapshot_value_preserves_hex_eq():
    Example(
        {
            "conftest.py": HEX_IF_EXISTING,
            "test_something.py": """\
from inline_snapshot import snapshot

def test_it():
    assert 5 == snapshot(0x5)
""",
        }
    ).run_inline(
        ["--inline-snapshot=update"],
        changed_files=snapshot({}),
        reported_categories=set(),
    )


@pytest.mark.parametrize(
    "assertion",
    [
        "assert 5 in snapshot([0x5])",
        "assert 5 <= snapshot(0x5)",
        "assert 5 >= snapshot(0x5)",
        "assert {5: 'x'} == snapshot({0x5: 'x'})",
        "assert {'x': 5} == snapshot({'x': 0x5})",
    ],
)
def test_snapshot_value_preserves_hex(assertion):
    Example(
        {
            "conftest.py": HEX_IF_EXISTING,
            "test_something.py": f"""\
from inline_snapshot import snapshot

def test_it():
    {assertion}
""",
        }
    ).run_inline(
        ["--inline-snapshot=update"],
        changed_files=snapshot({}),
        reported_categories=AnyThing(),
    )
