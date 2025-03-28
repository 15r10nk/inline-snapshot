import ast

from hypothesis import given
from hypothesis.strategies import text

from inline_snapshot import snapshot
from inline_snapshot._utils import triple_quote
from inline_snapshot.testing import Example


def test_string_update(check_update):
    # black --preview wraps strings to keep the line length.
    # string concatenation should produce updates.
    assert (
        check_update(
            'assert "ab" == snapshot("a" "b")', reported_flags="", flags="update"
        )
        == 'assert "ab" == snapshot("a" "b")'
    )

    assert (
        check_update(
            'assert "ab" == snapshot("a"\n "b")', reported_flags="", flags="update"
        )
        == 'assert "ab" == snapshot("a"\n "b")'
    )

    assert check_update(
        'assert "ab\\nc" == snapshot("a"\n "b\\nc")', flags="update"
    ) == snapshot(
        '''\
assert "ab\\nc" == snapshot("""\\
ab
c\\
""")\
'''
    )

    assert (
        check_update(
            'assert b"ab" == snapshot(b"a"\n b"b")', reported_flags="", flags="update"
        )
        == 'assert b"ab" == snapshot(b"a"\n b"b")'
    )


def test_string_newline(check_update):
    assert check_update('s = snapshot("a\\nb")', flags="update") == snapshot(
        '''\
s = snapshot("""\\
a
b\\
""")\
'''
    )

    assert check_update('s = snapshot("a\\"\\"\\"\\nb")', flags="update") == snapshot(
        """\
s = snapshot('''\\
a\"\"\"
b\\
''')\
"""
    )

    assert check_update(
        's = snapshot("a\\"\\"\\"\\n\\\'\\\'\\\'b")', flags="update"
    ) == snapshot(
        '''\
s = snapshot("""\\
a\\"\\"\\"
\'\'\'b\\
""")\
'''
    )

    assert check_update('s = snapshot(b"a\\nb")') == snapshot('s = snapshot(b"a\\nb")')

    assert check_update('s = snapshot("\\n\\\'")', flags="update") == snapshot(
        '''\
s = snapshot("""\\

'\\
""")\
'''
    )

    assert check_update('s = snapshot("\\n\\"")', flags="update") == snapshot(
        '''\
s = snapshot("""\\

"\\
""")\
'''
    )

    assert check_update("s = snapshot(\"'''\\n\\\"\")", flags="update") == snapshot(
        '''\
s = snapshot("""\\
\'\'\'
\\"\\
""")\
'''
    )

    assert check_update('s = snapshot("\\n\b")', flags="update") == snapshot(
        '''\
s = snapshot("""\\

\\x08\\
""")\
'''
    )


def test_string_quote_choice(check_update):
    assert check_update(
        "s = snapshot(\" \\'\\'\\' \\'\\'\\' \\\"\\\"\\\"\\nother_line\")",
        flags="update",
    ) == snapshot(
        '''\
s = snapshot("""\\
 \'\'\' \'\'\' \\"\\"\\"
other_line\\
""")\
'''
    )

    assert check_update(
        's = snapshot(" \\\'\\\'\\\' \\"\\"\\" \\"\\"\\"\\nother_line")', flags="update"
    ) == snapshot(
        """\
s = snapshot('''\\
 \\'\\'\\' \"\"\" \"\"\"
other_line\\
''')\
"""
    )

    assert check_update('s = snapshot("\\n\\"")', flags="update") == snapshot(
        '''\
s = snapshot("""\\

"\\
""")\
'''
    )

    assert check_update(
        "s=snapshot('\\n')", flags="update", reported_flags=""
    ) == snapshot("s=snapshot('\\n')")
    assert check_update(
        "s=snapshot('abc\\n')", flags="update", reported_flags=""
    ) == snapshot("s=snapshot('abc\\n')")
    assert check_update("s=snapshot('abc\\nabc')", flags="update") == snapshot(
        '''\
s=snapshot("""\\
abc
abc\\
""")\
'''
    )
    assert check_update("s=snapshot('\\nabc')", flags="update") == snapshot(
        '''\
s=snapshot("""\\

abc\\
""")\
'''
    )
    assert check_update("s=snapshot('a\\na\\n')", flags="update") == snapshot(
        '''\
s=snapshot("""\\
a
a
""")\
'''
    )

    assert (
        check_update(
            '''\
s=snapshot("""\\
a
""")\
''',
            flags="update",
        )
        == snapshot('s=snapshot("a\\n")')
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
                "test_something.py": '''\
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
                "test_something.py": '''\
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
