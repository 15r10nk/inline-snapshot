import itertools

from inline_snapshot import snapshot


def test_fix_list_fix(check_update):
    assert check_update(
        """assert [1,2]==snapshot([0+1,3])""", reported_flags="update,fix", flags="fix"
    ) == snapshot("""assert [1,2]==snapshot([0+1,2])""")


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
    ) == snapshot("""assert {1:1, 2:2}==snapshot({1:0+1, 2:2})""")


def test_fix_dict_remove(check_update):
    assert check_update(
        """assert {1:1}==snapshot({0:0, 1:0+1, 2:2})""",
        reported_flags="update,fix",
        flags="fix",
    ) == snapshot("assert {1:1}==snapshot({ 1:0+1, })")

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
        """assert {0:"before",1:1,2:"after"}==snapshot({0:"before", 1:0+1, 2:"after"})"""
    )


def test_fix_dict_with_non_literal_keys(check_update):
    assert check_update(
        """assert {1+2:"3"}==snapshot({1+2:"5"})""",
        reported_flags="update,fix",
        flags="fix",
    ) == snapshot('assert {1+2:"3"}==snapshot({1+2:"3"})')


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
            ],
        },
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
    codes = []

    for braces in ("[]", "()"):
        for s in itertools.product(stuff, repeat=3):
            flags = set().union(*[e[3] for e in s])
            name = ",".join(e[2] for e in s)
            print(flags)
            all_flags = {
                frozenset(x) - {""}
                for x in itertools.combinations_with_replacement(
                    flags | {""}, len(flags)
                )
            }
            print(all_flags)

            def build(l):
                values = [x for e in l for x in e]

                code = ", ".join(values)

                comma = ""
                if len(values) == 1 and braces == "()":
                    comma = ","

                return f"{braces[0]}{code}{comma}{braces[1]}"

            c1 = build(e[0] for e in s)
            c2 = build(e[1] for e in s)
            code = f"assert {c2}==snapshot({c1})"

            named_flags = ", ".join(flags)
            with subtests.test(f"{c1} -> {c2} <{named_flags}>"):

                s1 = source(code)
                print("source:", code)

                assert set(s1.flags) == flags

                assert ("fix" in flags) == s1.error

                for f in all_flags:
                    c3 = build([(e[1] if e[3] & f else e[0]) for e in s])
                    new_code = f"assert {c2}==snapshot({c3})"

                    print(f"{set(f)}:")
                    print("  ", code)
                    print("  ", new_code)

                    s2 = s1.run(*f)
                    assert s2.source == new_code
                    # assert s2.flags== flags-f
