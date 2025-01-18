import itertools
import sys

import pytest

from inline_snapshot import snapshot


def test_fix_list_fix(check_update):
    assert check_update(
        """assert [1,2]==snapshot([0+1,3])""", reported_flags="update,fix", flags="fix"
    ) == snapshot("assert [1,2]==snapshot([0+1,2])")


def test_fix_list_insert(check_update):
    assert check_update(
        """assert [1,2,3,4,5,6]==snapshot([0+1,3])""",
        reported_flags="update,fix",
        flags="fix",
    ) == snapshot("assert [1,2,3,4,5,6]==snapshot([0+1, 2, 3, 4, 5, 6])")


def test_fix_list_delete(check_update):
    assert check_update(
        """assert [1,5]==snapshot([0+1,2,3,4,5])""",
        reported_flags="update,fix",
        flags="fix",
    ) == snapshot("assert [1,5]==snapshot([0+1, 5])")


def test_fix_tuple_delete(check_update):
    assert check_update(
        """assert (1,5)==snapshot((0+1,2,3,4,5))""",
        reported_flags="update,fix",
        flags="fix",
    ) == snapshot("assert (1,5)==snapshot((0+1, 5))")


def test_fix_dict_change(check_update):
    assert check_update(
        """assert {1:1, 2:2}==snapshot({1:0+1, 2:3})""",
        reported_flags="update,fix",
        flags="fix",
    ) == snapshot("assert {1:1, 2:2}==snapshot({1:0+1, 2:2})")


def test_fix_dict_remove(check_update):
    assert check_update(
        """assert {1:1}==snapshot({0:0, 1:0+1, 2:2})""",
        reported_flags="update,fix",
        flags="fix",
    ) == snapshot("assert {1:1}==snapshot({1:0+1})")

    assert check_update(
        """assert {}==snapshot({0:0})""",
        reported_flags="fix",
        flags="fix",
    ) == snapshot("assert {}==snapshot({})")


def test_fix_dict_insert(check_update):
    assert check_update(
        """assert {0:"before",1:1,2:"after"}==snapshot({1:0+1})""",
        reported_flags="update,fix",
        flags="fix",
    ) == snapshot(
        'assert {0:"before",1:1,2:"after"}==snapshot({0: "before", 1:0+1, 2: "after"})'
    )


def test_fix_dict_with_non_literal_keys(check_update):
    assert check_update(
        """assert {1+2:"3"}==snapshot({1+2:"5"})""",
        reported_flags="fix",
        flags="fix",
    ) == snapshot('assert {1+2:"3"}==snapshot({1+2:"3"})')


@pytest.mark.skipif(
    sys.version_info < (3, 8), reason="dirty equals has dropped the 3.7 support"
)
def test_no_update_for_dirty_equals(check_update):
    assert (
        check_update(
            """\
from dirty_equals import IsInt
assert {5:5,2:2}==snapshot({5:IsInt(),2:1+1})
""",
            reported_flags="update",
            flags="update",
        )
        == snapshot(
            """\
from dirty_equals import IsInt
assert {5:5,2:2}==snapshot({5:IsInt(),2:2})
"""
        )
    )


# @pytest.mark.skipif(not hasattr(ast, "unparse"), reason="ast.unparse not available")
def test_preserve_case_from_original_mr(check_update):
    assert (
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
)
""",
            reported_flags="update,fix",
            flags="fix",
        )
        == snapshot(
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
        "a": 1,
        "b": {
            "c": 2 * 1 + 0,
            "d": [
                int(3),
                4,
                5,
            ]},
        "e": ({"f": 6, "g": 7},),
    }
)
"""
        )
    )


stuff = [
    (["5"], [], "delete", {"fix"}),
    ([], ["8"], "insert", {"fix"}),
    (["2+2"], ["4"], "update", {"update"}),
    (["3"], ["3"], "no_change", set()),
]


def test_generic(source, subtests):
    for braces in ("[]", "()", "{}"):
        for value_specs in itertools.product(stuff, repeat=3):
            flags = set().union(*[e[3] for e in value_specs])
            all_flags = {
                frozenset(x) - {""}
                for x in itertools.combinations_with_replacement(
                    flags | {""}, len(flags)
                )
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

            c1 = build(spec[0] for spec in value_specs)
            c2 = build(spec[1] for spec in value_specs)
            code = f"assert {c2}==snapshot({c1})"

            named_flags = ", ".join(flags)

            with subtests.test(f"{c1} -> {c2} <{named_flags}>"):
                s1 = source(code)
                print("source:", code)

                assert set(s1.flags) == flags

                assert ("fix" in flags) == s1.error

                for f in all_flags:
                    c3 = build(
                        [(spec[1] if spec[3] & f else spec[0]) for spec in value_specs]
                    )
                    new_code = f"assert {c2}==snapshot({c3})"

                    print(f"{set(f)}:")
                    print("  ", code)
                    print("  ", new_code)
                    s2 = s1.run(*f)
                    assert s2.source == new_code
                    # assert s2.flags== flags-f
