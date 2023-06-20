import ast
import textwrap

import pytest
from hypothesis import given
from hypothesis.strategies import text

from inline_snapshot import _inline_snapshot
from inline_snapshot import snapshot
from inline_snapshot._inline_snapshot import Flags
from inline_snapshot._inline_snapshot import snapshot_env
from inline_snapshot._inline_snapshot import triple_quote
from inline_snapshot._rewrite_code import ChangeRecorder


def test_snapshot_eq():
    with snapshot_env():
        assert 1 == snapshot(1)
        assert snapshot(1) == 1


def test_disabled():
    with snapshot_env():
        _inline_snapshot._active = False
        with pytest.raises(AssertionError) as excinfo:
            assert 2 == snapshot()

    assert str(excinfo.value) == snapshot(
        "your snapshot is missing a value run pytest with --inline-snapshot=create"
    )


@pytest.fixture()
def check_update(tmp_path):
    filecount = 1

    def w(source, *, flags="", reported_flags=None):
        flags = Flags({*flags.split(",")})
        if reported_flags is None:
            reported_flags = flags
        else:
            reported_flags = Flags({*reported_flags.split(",")})

        nonlocal filecount
        filename = tmp_path / f"test_{filecount}.py"
        filecount += 1

        prefix = """\"\"\"
PYTEST_DONT_REWRITE
\"\"\"
from inline_snapshot import snapshot

"""

        filename.write_text(prefix + textwrap.dedent(source))

        with snapshot_env():
            with ChangeRecorder().activate() as recorder:
                _inline_snapshot._update_flags = flags

                try:
                    exec(compile(filename.read_text(), filename, "exec"))
                except AssertionError:
                    assert reported_flags.fix
                finally:
                    _inline_snapshot._active = False

                assert len(_inline_snapshot.snapshots) == 1

                snapshot_flags = set()

                for snapshot in _inline_snapshot.snapshots.values():
                    snapshot_flags |= snapshot._flags
                    snapshot._change()

                assert reported_flags.to_set() == snapshot_flags, snapshot_flags

                changes = recorder.changes()

                assert len(changes) == 1

                print("changes:")
                recorder.dump()
                recorder.fix_all(tags=["inline_snapshot"])

        return filename.read_text()[len(prefix) :]

    return w


def test_comparison(check_update):
    assert check_update("assert 5==snapshot()", flags="create") == snapshot(
        "assert 5==snapshot(5)"
    )

    assert check_update("assert 5==snapshot(9)", flags="fix") == snapshot(
        "assert 5==snapshot(5)"
    )

    assert check_update('assert "a"==snapshot("""a""")', flags="update") == snapshot(
        'assert "a"==snapshot("a")'
    )

    assert (
        check_update(
            """
            for a in [1,1,1]:
                assert a==snapshot()
            """,
            flags="create",
        )
        == snapshot(
            """
for a in [1,1,1]:
    assert a==snapshot(1)
"""
        )
    )

    assert (
        check_update(
            """
            for a in [1,1,1]:
                assert a==snapshot(2)
            """,
            flags="fix",
        )
        == snapshot(
            """
for a in [1,1,1]:
    assert a==snapshot(1)
"""
        )
    )


def test_ge(check_update):
    assert check_update("assert 5<=snapshot()", flags="create") == snapshot(
        "assert 5<=snapshot(5)"
    )

    assert check_update("assert 5<=snapshot()", reported_flags="create") == snapshot(
        "assert 5<=snapshot()"
    )

    assert (
        check_update(
            """
s=snapshot({"v": 7, "q": 4})
assert 5<=s["v"]
assert 5==s["q"]
""",
            flags="fix",
            reported_flags="fix,trim",
        )
        == snapshot(
            """
s=snapshot({"v": 7, "q": 5})
assert 5<=s["v"]
assert 5==s["q"]
"""
        )
    )

    assert (
        check_update(
            """
s=snapshot({"q": 4})
assert 5<=s["v"]
assert 5==s["q"]
""",
            flags="fix",
            reported_flags="fix,create",
        )
        == snapshot(
            """
s=snapshot({"q": 5})
assert 5<=s["v"]
assert 5==s["q"]
"""
        )
    )

    assert check_update("assert 5<=snapshot(9)", flags="trim") == snapshot(
        "assert 5<=snapshot(5)"
    )

    assert check_update("assert 5<=snapshot(3)", flags="fix") == snapshot(
        "assert 5<=snapshot(5)"
    )

    assert check_update("assert snapshot(3) >= 5", flags="fix") == snapshot(
        "assert snapshot(5) >= 5"
    )

    assert check_update("assert 5<=snapshot(5)") == snapshot("assert 5<=snapshot(5)")

    assert check_update(
        "for i in range(5): assert i <=snapshot(2)", flags="fix"
    ) == snapshot("for i in range(5): assert i <=snapshot(4)")

    assert check_update(
        "for i in range(5): assert i <=snapshot(10)", flags="trim"
    ) == snapshot("for i in range(5): assert i <=snapshot(4)")


def test_le(check_update):
    assert check_update("assert 5>=snapshot()", flags="create") == snapshot(
        "assert 5>=snapshot(5)"
    )

    assert (
        check_update(
            """
s=snapshot({"v": 3, "q": 4})
assert 5>=s["v"]
assert 5==s["q"]
""",
            flags="fix",
            reported_flags="fix,trim",
        )
        == snapshot(
            """
s=snapshot({"v": 3, "q": 5})
assert 5>=s["v"]
assert 5==s["q"]
"""
        )
    )

    assert (
        check_update(
            """
s=snapshot({"q": 4})
assert 5>=s["v"]
assert 5==s["q"]
""",
            flags="fix",
            reported_flags="fix,create",
        )
        == snapshot(
            """
s=snapshot({"q": 5})
assert 5>=s["v"]
assert 5==s["q"]
"""
        )
    )

    assert check_update("assert 5>=snapshot(2)", flags="trim") == snapshot(
        "assert 5>=snapshot(5)"
    )

    assert check_update("assert 5>=snapshot(8)", flags="fix") == snapshot(
        "assert 5>=snapshot(5)"
    )

    assert check_update("assert snapshot(8) <= 5", flags="fix") == snapshot(
        "assert snapshot(5) <= 5"
    )

    assert check_update("assert 5>=snapshot(5)") == snapshot("assert 5>=snapshot(5)")

    assert check_update(
        "for i in range(5): assert i >=snapshot(2)", flags="fix"
    ) == snapshot("for i in range(5): assert i >=snapshot(0)")

    assert check_update(
        "for i in range(5): assert i >=snapshot(-10)", flags="trim"
    ) == snapshot("for i in range(5): assert i >=snapshot(0)")


def test_contains(check_update):
    assert check_update("assert 5 in snapshot()", flags="create") == snapshot(
        "assert 5 in snapshot([5])"
    )

    assert check_update("assert 5 in snapshot([])", flags="fix") == snapshot(
        "assert 5 in snapshot([5])"
    )

    assert check_update("assert 5 in snapshot([2])", flags="fix,trim") == snapshot(
        "assert 5 in snapshot([5])"
    )

    assert check_update("assert 5 in snapshot([2,5])", flags="trim") == snapshot(
        "assert 5 in snapshot([5])"
    )

    assert check_update(
        "for i in range(5): assert i in snapshot([0,1,2,3,4,5,6])", flags="trim"
    ) == snapshot("for i in range(5): assert i in snapshot([0, 1, 2, 3, 4])")

    assert (
        check_update(
            """
s=snapshot()
assert 4 in s
assert 5 in s
assert 5 in s
""",
            flags="create",
        )
        == snapshot(
            """
s=snapshot([4, 5])
assert 4 in s
assert 5 in s
assert 5 in s
"""
        )
    )


def test_getitem(check_update):
    assert check_update('assert 5 == snapshot()["test"]', flags="create") == snapshot(
        'assert 5 == snapshot({"test": 5})["test"]'
    )

    assert check_update(
        "for i in range(3): assert i in snapshot()[str(i)]", flags="create"
    ) == snapshot(
        'for i in range(3): assert i in snapshot({"0": [0], "1": [1], "2": [2]})[str(i)]'
    )

    assert check_update(
        'for i in range(3): assert i in snapshot({"0": [0], "1": [1], "2": [2]})[str(i)]'
    ) == snapshot(
        'for i in range(3): assert i in snapshot({"0": [0], "1": [1], "2": [2]})[str(i)]'
    )

    assert check_update(
        'for i in range(2): assert i in snapshot({"0": [0], "1": [1], "2": [2]})[str(i)]',
        flags="trim",
    ) == snapshot(
        'for i in range(2): assert i in snapshot({"0": [0], "1": [1]})[str(i)]'
    )

    assert check_update(
        'for i in range(3): assert i in snapshot({"0": [0], "1": [1,2], "2": [4]})[str(i)]',
        flags="fix,trim",
    ) == snapshot(
        'for i in range(3): assert i in snapshot({"0": [0], "1": [1], "2": [2]})[str(i)]'
    )

    assert check_update(
        'for i in range(3): assert i in snapshot({"0": [0], "1": [1,2], "2": [4]})[str(i)]',
        flags="fix",
        reported_flags="fix,trim",
    ) == snapshot(
        'for i in range(3): assert i in snapshot({"0": [0], "1": [1, 2], "2": [4, 2]})[str(i)]'
    )

    assert check_update(
        'for i in range(3): assert i in snapshot({"0": [0], "1": [1,2], "2": [2]})[str(i)]',
        flags="trim",
    ) == snapshot(
        'for i in range(3): assert i in snapshot({"0": [0], "1": [1], "2": [2]})[str(i)]'
    )

    assert check_update(
        "assert 4 in snapshot({2:[4],3:[]})[2]", flags="trim"
    ) == snapshot("assert 4 in snapshot({2: [4]})[2]")

    assert check_update(
        "assert 5 in snapshot({2:[4],3:[]})[2]", flags="fix", reported_flags="fix,trim"
    ) == snapshot("assert 5 in snapshot({2: [4, 5], 3: []})[2]")

    assert check_update(
        "assert 5 in snapshot({2:[4],3:[]})[2]", flags="fix,trim"
    ) == snapshot("assert 5 in snapshot({2: [5]})[2]")

    assert check_update(
        "assert 5 in snapshot({3:[1]})[2]", flags="create", reported_flags="create,trim"
    ) == snapshot("assert 5 in snapshot({2: [5], 3: [1]})[2]")

    assert (
        check_update(
            """
s=snapshot()
assert 5 == s["q"]
assert 5 == s["q"]
        """,
            flags="create",
        )
        == snapshot(
            """
s=snapshot({"q": 5})
assert 5 == s["q"]
assert 5 == s["q"]
"""
        )
    )


def test_assert(check_update):
    assert check_update("assert 2 == snapshot(5)", reported_flags="fix")


def test_plain(check_update):
    assert check_update("s = snapshot(5)", flags="") == snapshot("s = snapshot(5)")

    assert check_update(
        "s = snapshot()", flags="", reported_flags="create"
    ) == snapshot("s = snapshot()")


def test_string_newline(check_update):
    assert check_update('s = snapshot("a\\nb")', flags="update") == snapshot(
        '''s = snapshot("""a
b""")'''
    )

    assert check_update('s = snapshot("a\\"\\"\\"\\nb")', flags="update") == snapshot(
        """s = snapshot('''a\"\"\"
b''')"""
    )

    assert check_update(
        's = snapshot("a\\"\\"\\"\\n\\\'\\\'\\\'b")', flags="update"
    ) == snapshot(
        '''s = snapshot("""a\\"\\"\\"
\'\'\'b""")'''
    )

    assert check_update('s = snapshot(b"a\\nb")') == snapshot('s = snapshot(b"a\\nb")')

    assert check_update('s = snapshot("\\n\\\'")', flags="update") == snapshot(
        '''s = snapshot("""
'""")'''
    )

    assert check_update('s = snapshot("\\n\\"")', flags="update") == snapshot(
        """s = snapshot('''
"''')"""
    )

    assert check_update("s = snapshot(\"'''\\n\\\"\")", flags="update") == snapshot(
        '''s = snapshot("""\'\'\'
\\"""")'''
    )

    assert check_update('s = snapshot("\\n\b")', flags="update") == snapshot(
        '''s = snapshot("""
\\x08""")'''
    )


def test_string_quote_choice(check_update):
    assert check_update(
        "s = snapshot(\" \\'\\'\\' \\'\\'\\' \\\"\\\"\\\"\\n\")", flags="update"
    ) == snapshot(
        '''s = snapshot(""" \'\'\' \'\'\' \\"\\"\\"
""")'''
    )

    assert check_update(
        's = snapshot(" \\\'\\\'\\\' \\"\\"\\" \\"\\"\\"\\n")', flags="update"
    ) == snapshot(
        """s = snapshot(''' \\'\\'\\' \"\"\" \"\"\"
''')"""
    )

    assert check_update('s = snapshot("\\n\\"")', flags="update") == snapshot(
        """s = snapshot('''
"''')"""
    )


@given(s=text())
def test_string_convert(s):
    print(s)
    assert ast.literal_eval(triple_quote(s)) == s


def test_flags_repr():
    assert repr(Flags({"update"})) == "Flags({'update'})"


def test_format_file(check_update):
    assert check_update(
        'assert ["aaaaaaaaaaaaaaaaa"] * 5 == snapshot()\n', flags="create"
    ) == snapshot(
        """assert ["aaaaaaaaaaaaaaaaa"] * 5 == snapshot(
    [
        "aaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaa",
        "aaaaaaaaaaaaaaaaa",
    ]
)
"""
    )


def test_format_value(check_update):
    assert check_update(
        'assert ["aaaaaaaaaaaaaaaaa"] * 5==  snapshot()\n', flags="create"
    ) == snapshot(
        """assert ["aaaaaaaaaaaaaaaaa"] * 5==  snapshot([
    "aaaaaaaaaaaaaaaaa",
    "aaaaaaaaaaaaaaaaa",
    "aaaaaaaaaaaaaaaaa",
    "aaaaaaaaaaaaaaaaa",
    "aaaaaaaaaaaaaaaaa",
])
"""
    )
