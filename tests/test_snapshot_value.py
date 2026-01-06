"""Tests for snapshot_value parameter in customize hooks."""

from inline_snapshot import snapshot
from inline_snapshot.testing import Example


def test_snapshot_value_in_list():
    """Test that snapshot_value works with list elements."""
    Example(
        {
            "tests/conftest.py": """\
from inline_snapshot import customize, snapshot

old_new_mapping={}

@customize
def double_if_old_exists(value, builder, snapshot_value):
    if isinstance(value, int):
        old_new_mapping[value]=str(snapshot_value)
        return builder.create_value(value)

""",
            "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_it():
    # When we fix, the runtime value [1, 2, 3, 4, 5, 6] is compared with snapshot [1, 8, 3, 4, 5, 0]
    # Each runtime element should see its corresponding snapshot element:
    # 1 -> 1, 2 -> 8, 3 -> 3, 4 -> 4, 5 -> 5, 6 -> 0
    assert snapshot([1, 8, 3,4,5,0]) == [1, 2, 3,4,5,6]
    from conftest import old_new_mapping

    assert old_new_mapping==snapshot()
""",
        }
    ).run_pytest(
        ["--inline-snapshot=fix,create"],
        # Runtime [1, 2, 3, 4, 5, 6] compared with snapshot [1, 8, 3, 4, 5, 0]
        # Each runtime value gets the corresponding snapshot value:
        # 1->1, 2->8, 3->3, 4->4, 5->5, 6->0
        returncode=1,  # Expect error due to missing snapshot being created
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_it():
    # When we fix, the runtime value [1, 2, 3, 4, 5, 6] is compared with snapshot [1, 8, 3, 4, 5, 0]
    # Each runtime element should see its corresponding snapshot element:
    # 1 -> 1, 2 -> 8, 3 -> 3, 4 -> 4, 5 -> 5, 6 -> 0
    assert snapshot([1, 2, 3,4,5,6]) == [1, 2, 3,4,5,6]
    from conftest import old_new_mapping

    assert old_new_mapping==snapshot({1: "1", 2: "8", 3: "3", 4: "4", 5: "5", 6: "0"})
"""
            }
        ),
    )
