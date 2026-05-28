"""Tests for snapshot_value parameter in customize hooks."""

from inline_snapshot import snapshot
from inline_snapshot.testing import Example


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
