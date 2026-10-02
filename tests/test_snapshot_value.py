"""Tests for snapshot_value parameter in customize hooks."""

import pytest
from dirty_equals import AnyThing

from inline_snapshot import Is
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


@pytest.mark.parametrize(
    "value, existing, child",
    [
        ("[[5]]", "[[0x5]]", "builder.create_list(value)"),
        ("[(5,)]", "[(0x5,)]", "builder.create_tuple(value)"),
        ("[{5: 5}]", "[{0x5: 0x5}]", "builder.create_dict(value)"),
        ("[5]", "[int(0x5)]", "builder.create_call(int, [value])"),
    ],
)
def test_snapshot_value_in_nested_builder(value, existing, child):
    Example(
        {
            "conftest.py": HEX_IF_EXISTING
            + f"""\

@customize
def nested_builder(value, builder):
    if isinstance(value, list):
        return builder.create_list([{child} for value in value])
""",
            "test_something.py": f"""\
from inline_snapshot import snapshot

def test_it():
    assert {value} == snapshot({existing})
""",
        }
    ).run_inline(
        ["--inline-snapshot=update"],
        reported_categories=set(),
    )


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


@pytest.mark.parametrize("old, flag", [(5, "fix"), (6, "update"), (None, "create")])
@pytest.mark.parametrize(
    "value, existing, result, node",
    [
        ("[6]", "[{old}]", "[IsInt()]", "matcher"),
        ("[[6]]", "[[{old}]]", "[[IsInt()]]", "builder.create_list([matcher])"),
        ("[(6,)]", "[({old},)]", "[(IsInt(),)]", "builder.create_tuple((matcher,))"),
        (
            "[{'x': 6}]",
            '[{{"x": {old}}}]',
            '[{"x": IsInt()}]',
            "builder.create_dict({'x': matcher})",
        ),
        (
            "[(6,)]",
            "[tuple([{old}])]",
            "[tuple([IsInt()])]",
            "builder.create_call(tuple, [builder.create_list([matcher])])",
        ),
        (
            "[{'x': 6}]",
            "[dict(x={old})]",
            "[dict(x=IsInt())]",
            "builder.create_call(dict, [], {'x': matcher})",
        ),
        (
            "[{6}]",
            "[{{{old}}}]",
            "[{0x6}]",
            "builder.create_set({builder.create_code('0x6')})",
        ),
    ],
)
def test_explicit_matcher_inherits_category(old, flag, value, existing, result, node):
    def code(expected):
        return f"""\
from inline_snapshot import snapshot
from dirty_equals import IsInt

def test_it():
    assert {value} == snapshot({expected})
"""

    example = Example(
        {
            "conftest.py": f"""\
from inline_snapshot.plugin import customize
from dirty_equals import IsInt

@customize
def custom(value, builder):
    if isinstance(value, list):
        matcher = builder.create_call(IsInt, [])
        return builder.create_list([{node}])
""",
            "test_something.py": code(
                existing.format(old=old) if old is not None else ""
            ),
        }
    )
    example.run_inline(
        [f"--inline-snapshot={flag}"],
        changed_files=Is({"test_something.py": code(result)}),
    ).run_inline(reported_categories=set())

    other_flag = "update" if flag == "fix" else "fix"
    example.run_inline(
        [f"--inline-snapshot={other_flag}"],
        reported_categories=Is({flag}),
    )


@pytest.mark.parametrize(
    "flag, expected",
    [
        ("fix", "[[6], 9]"),
        ("update", "[[IsInt()], 8]"),
    ],
)
def test_explicit_matcher_uses_nearest_known_parent(flag, expected):
    def code(value):
        return f"""\
from inline_snapshot import snapshot
from dirty_equals import IsInt

def test_it():
    assert [[6], 9] == snapshot({value})
"""

    Example(
        {
            "conftest.py": """\
from inline_snapshot.plugin import customize
from dirty_equals import IsInt

@customize
def custom(value, builder):
    if isinstance(value, list) and len(value) == 1:
        return builder.create_list([builder.create_call(IsInt, [])])
""",
            "test_something.py": code("[[6], 8]"),
        }
    ).run_inline(
        [f"--inline-snapshot={flag}"],
        reported_categories={"fix", "update"},
        changed_files=Is({"test_something.py": code(expected)}),
    )


def test_explicit_matcher_unknown_parent_inherits_fix():
    Example(
        {
            "conftest.py": """\
from inline_snapshot.plugin import customize
from dirty_equals import IsInt

@customize
def custom(value, builder):
    if isinstance(value, list):
        return builder.create_list([
            builder.create_list([builder.create_call(IsInt, [])]),
            builder.create_code("9"),
        ])
""",
            "test_something.py": """\
from inline_snapshot import snapshot
from dirty_equals import IsInt

def test_it():
    assert [[6], 9] == snapshot([[6], 8])
""",
        }
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files={"test_something.py": """\
from inline_snapshot import snapshot
from dirty_equals import IsInt

def test_it():
    assert [[6], 9] == snapshot([[IsInt()], 9])
"""},
    )


def test_reused_builder_node_does_not_retain_original_value():
    Example(
        {
            "conftest.py": """\
from inline_snapshot.plugin import customize
from dirty_equals import IsInt

shared = None

@customize
def custom(value, builder):
    global shared
    if shared is None:
        shared = builder.create_call(IsInt, [])
    if isinstance(value, int):
        return shared
    if isinstance(value, list):
        return builder.create_list([shared])
""",
            "test_something.py": """\
from inline_snapshot import snapshot
from dirty_equals import IsInt

def test_it():
    assert 6 == snapshot(IsInt())
    assert [7] == snapshot([6])
""",
        }
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files={"test_something.py": """\
from inline_snapshot import snapshot
from dirty_equals import IsInt

def test_it():
    assert 6 == snapshot(IsInt())
    assert [7] == snapshot([IsInt()])
"""},
    ).run_inline(
        reported_categories=set()
    )
