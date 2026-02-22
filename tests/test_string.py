import ast

from hypothesis import given
from hypothesis.strategies import text

from inline_snapshot import snapshot
from inline_snapshot._snapshot_arg import snapshot_arg
from inline_snapshot._utils import triple_quote
from inline_snapshot.extra import Transformed
from inline_snapshot.testing import Example
from tests.conftest import check_update


def test_string_update():
    # black --preview wraps strings to keep the line length.
    # string concatenation should produce updates.
    check_update(
        'assert "ab" == snapshot("a" "b")',
        reported_flags="",
        flags="update",
        expected_code='assert "ab" == snapshot("a" "b")',
    )

    check_update(
        'assert "ab" == snapshot("a"\n "b")',
        reported_flags="",
        flags="update",
        expected_code="""\
assert "ab" == snapshot("a"
 "b")\
""",
    )

    check_update(
        'assert "ab\\nc" == snapshot("a"\n "b\\nc")',
        flags="update",
        expected_code='''\
assert "ab\\nc" == snapshot("""\\
ab
c\\
""")\
''',
    )

    check_update(
        'assert b"ab" == snapshot(b"a"\n b"b")',
        reported_flags="",
        flags="update",
        expected_code="""\
assert b"ab" == snapshot(b"a"
 b"b")\
""",
    )


def test_string_newline():
    check_update2(
        '"a\\nb"',
        snapshot(
            '''\
s = snapshot("""\\
a
b\\
""")\
'''
        ),
    )

    check_update2(
        '"a\\"\\"\\"\\nb"',
        snapshot(
            """\
s = snapshot('''\\
a\"\"\"
b\\
''')\
"""
        ),
    )

    check_update2(
        '"a\\"\\"\\"\\n\\\'\\\'\\\'b"',
        '''\
s = snapshot("""\\
a\\"\\"\\"
\'\'\'b\\
""")\
''',
    )

    check_update2('b"a\\nb"', snapshot('s = snapshot(b"a\\nb")'), reported_flags="")

    check_update2(
        '"\\n\\\'"',
        snapshot(
            '''\
s = snapshot("""\\

'\\
""")\
'''
        ),
    )

    check_update2(
        '"\\n\\""',
        snapshot(
            '''\
s = snapshot("""\\

"\\
""")\
'''
        ),
    )

    check_update2(
        "\"'''\\n\\\"\"",
        snapshot(
            '''\
s = snapshot("""\\
\'\'\'
\\"\\
""")\
'''
        ),
    )

    check_update2(
        '"\\n\b"',
        snapshot(
            '''\
s = snapshot("""\\

\\x08\\
""")\
'''
        ),
    )


def check_update2(string, expected_str=..., reported_flags="update"):
    check_update(
        f"s = snapshot({string})\nassert {string} == s",
        reported_flags="",
        flags="update",
        expected_code=Transformed(lambda v: v.split("assert")[0].strip(), expected_str),
    )


def test_string_quote_choice():
    check_update2(
        "\" \\'\\'\\' \\'\\'\\' \\\"\\\"\\\"\\nother_line\"",
        snapshot(
            '''\
s = snapshot("""\\
 \'\'\' \'\'\' \\"\\"\\"
other_line\\
""")\
'''
        ),
    )

    check_update2(
        '" \\\'\\\'\\\' \\"\\"\\" \\"\\"\\"\\nother_line"',
        snapshot(
            """\
s = snapshot('''\\
 \\'\\'\\' \"\"\" \"\"\"
other_line\\
''')\
"""
        ),
    )

    check_update2(
        '"\\n\\""',
        snapshot(
            '''\
s = snapshot("""\\

"\\
""")\
'''
        ),
    )

    check_update2("'\\n'", snapshot("s = snapshot('\\n')"), reported_flags="")
    check_update2("'abc\\n'", snapshot("s = snapshot('abc\\n')"), reported_flags="")

    check_update2(
        "'abc\\nabc'",
        snapshot(
            '''\
s = snapshot("""\\
abc
abc\\
""")\
'''
        ),
    )

    check_update2(
        "'\\nabc'",
        snapshot(
            '''\
s = snapshot("""\\

abc\\
""")\
'''
        ),
    )

    check_update2(
        "'a\\na\\n'",
        snapshot(
            '''\
s = snapshot("""\\
a
a
""")\
'''
        ),
    )

    check_update2(
        '''"""\\
a
"""''',
        snapshot('s = snapshot("a\\n")'),
    )


@given(s=text())
def test_string_convert(s):
    print(s)
    assert ast.literal_eval(triple_quote(s)) == s


def test_newline():
    Example(
        """\
from inline_snapshot import snapshot

def test_a():
    assert "a\\r\\nb" == snapshot()
"""
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "tests/test_something.py": '''\
from inline_snapshot import snapshot

def test_a():
    assert "a\\r\\nb" == snapshot("""\\
a\\r
b\\
""")
'''
            }
        ),
    )


def test_trailing_whitespaces():
    Example(
        """\
from inline_snapshot import snapshot

def test_a():
    assert "a   \\r\\nb   \\nc   " == snapshot()
"""
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "tests/test_something.py": '''\
from inline_snapshot import snapshot

def test_a():
    assert "a   \\r\\nb   \\nc   " == snapshot("""\\
a   \\r
b   \\n\\
c   \\
""")
'''
            }
        ),
    )


def test_fix_remove_triple_quotes():
    Example(
        """\
from inline_snapshot import snapshot

def test_a():
    assert "" == snapshot('''
a
b\
''')
"""
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_a():
    assert "" == snapshot("")
"""
            }
        ),
    )


def test_update_remove_triple_quotes():
    Example(
        """\
from inline_snapshot import snapshot

def test_a():
    assert "" == snapshot(\"\"\"\"\"\")
"""
    ).run_inline(
        ["--inline-snapshot=update"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_a():
    assert "" == snapshot("")
"""
            }
        ),
    )



