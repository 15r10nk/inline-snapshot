import itertools
import sys

import pytest
from dirty_equals import AnyThing

from inline_snapshot._inline_snapshot import snapshot
from inline_snapshot.testing._example import Example
from tests.conftest import check_update


def test_fix_list_fix():
    check_update(
        """assert [1,2]==snapshot([0+1,3])""",
        reported_flags={"fix", "update"},
        flags="fix",
        expected_code="assert [1,2]==snapshot([0+1,2])",
    )


def test_fix_list_insert():
    check_update(
        """assert [1,2,3,4,5,6]==snapshot([0+1,3])""",
        reported_flags={"fix", "update"},
        flags="fix",
        expected_code="assert [1,2,3,4,5,6]==snapshot([0+1, 2, 3, 4, 5, 6])",
    )


def test_fix_list_delete():
    check_update(
        """assert [1,5]==snapshot([0+1,2,3,4,5])""",
        reported_flags={"fix", "update"},
        flags="fix",
        expected_code="assert [1,5]==snapshot([0+1, 5])",
    )


def test_fix_tuple_delete():
    check_update(
        """assert (1,5)==snapshot((0+1,2,3,4,5))""",
        reported_flags={"fix", "update"},
        flags="fix",
        expected_code="assert (1,5)==snapshot((0+1, 5))",
    )


def test_fix_dict_change():
    check_update(
        """assert {1:1, 2:2}==snapshot({1:0+1, 2:3})""",
        reported_flags={"fix", "update"},
        flags="fix",
        expected_code="assert {1:1, 2:2}==snapshot({1:0+1, 2:2})",
    )


def test_fix_dict_remove():
    check_update(
        """assert {1:1}==snapshot({0:0, 1:0+1, 2:2})""",
        reported_flags={"fix", "update"},
        flags="fix",
        expected_code="assert {1:1}==snapshot({1:0+1})",
    )

    check_update(
        """assert {}==snapshot({0:0})""",
        flags="fix",
        expected_code="assert {}==snapshot({})",
    )


def test_fix_dict_insert():
    check_update(
        """assert {0:"before",1:1,2:"after"}==snapshot({1:0+1})""",
        reported_flags={"fix", "update"},
        flags="fix",
        expected_code='assert {0:"before",1:1,2:"after"}==snapshot({0: "before", 1:0+1, 2: "after"})',
    )


def test_fix_dict_with_non_literal_keys():
    check_update(
        """assert {1+2:"3"}==snapshot({1+2:"5"})""",
        flags="fix",
        expected_code='assert {1+2:"3"}==snapshot({1+2:"3"})',
    )


@pytest.mark.skipif(
    sys.version_info < (3, 8), reason="dirty equals has dropped the 3.7 support"
)
def test_no_update_for_dirty_equals():
    check_update(
        """\
from dirty_equals import IsInt
assert {5:5,2:2}==snapshot({5:IsInt(),2:1+1})\
""",
        flags="update",
        expected_code="""\
from dirty_equals import IsInt
assert {5:5,2:2}==snapshot({5:IsInt(),2:2})\
""",
    )


# @pytest.mark.skipif(not hasattr(ast, "unparse"), reason="ast.unparse not available")
def test_preserve_case_from_original_mr():
    check_update(
        """\
left = {
    "a": 1,
    "b": {
        "c": 2,
        "d": [
3,
4,
5,
        ],
    },
    "e": (
        {
"f": 6,
"g": 7,
        },
    ),
}
assert left == snapshot(
    {
        "a": 10,
        "b": {
"c": 2 * 1 + 0,
"d": [
    int(3),
    40,
    5,
],
"h": 8,
        },
        "e": (
{
    "f": 3 + 3,
},
9,
        ),
    }
)\
""",
        reported_flags={"fix", "update"},
        flags="fix",
        expected_code="""\
left = {
    "a": 1,
    "b": {
        "c": 2,
        "d": [
3,
4,
5,
        ],
    },
    "e": (
        {
"f": 6,
"g": 7,
        },
    ),
}
assert left == snapshot(
    {
        "a": 1,
        "b": {
"c": 2 * 1 + 0,
"d": [
    int(3),
    4,
    5,
]},
        "e": (
{
    "f": 3 + 3, "g": 7},),
    }
)\
""",
    )


stuff = [
    (["5"], [], "delete", {"fix"}),
    ([], ["8"], "insert", {"fix"}),
    (["2+2"], ["4"], "update", {"update"}),
    (["3"], ["3"], "no_change", set()),
]


@pytest.mark.parametrize("braces", ["[]", "()", "{}"])
@pytest.mark.parametrize("value_specs", itertools.product(stuff, repeat=3))
def test_generic(braces, value_specs):
    flags = set().union(*[e[3] for e in value_specs])
    all_flags = {
        frozenset(x) - {""}
        for x in itertools.combinations_with_replacement(flags | {""}, len(flags))
    }

    def build(value_lists):
        value_lists = list(value_lists)

        if braces == "{}":
            values = [
                f"{i}: {value_list[0]}"
                for i, value_list in enumerate(value_lists)
                if value_list
            ]
        else:
            values = [x for value_list in value_lists for x in value_list]

        code = ", ".join(values)

        comma = ""
        if len(values) == 1 and braces == "()":
            comma = ","

        return f"{braces[0]}{code}{comma}{braces[1]}"

    def gen_code(a, b):
        return f"""\
from inline_snapshot import snapshot
def test_a():
    assert {a}==snapshot({b})
"""

    c1 = build(spec[0] for spec in value_specs)
    c2 = build(spec[1] for spec in value_specs)
    code = gen_code(c2, c1)

    # s1 = source(code)
    e1 = Example(code)

    # check that the flags are reported
    e1.run_inline(
        reported_categories=sorted(flags),
        raises=(
            snapshot("AssertionError") if "fix" in flags else snapshot("<no exception>")
        ),
    )

    for f in all_flags:
        c3 = build([(spec[1] if spec[3] & f else spec[0]) for spec in value_specs])
        new_code = gen_code(c2, c3)

        f = ",".join(sorted(f))
        e2 = e1.run_inline(
            [f"--inline-snapshot={f}"] if f else [],
            raises=AnyThing(),
        )
        assert e2.read_file("tests/test_something.py") == new_code
