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
        reported_flags=set(),
        flags="update",
        expected_code='assert "ab" == snapshot("a" "b")',
    )

    check_update(
        'assert "ab" == snapshot("a"\n "b")',
        reported_flags=set(),
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
        reported_flags=set(),
        flags="update",
        expected_code="""\
assert b"ab" == snapshot(b"a"
 b"b")\
""",
    )


def test_string_newline():
    check_string_update(
        '"a\\nb"',
        snapshot('''\
"""\\
a
b\\
"""\
'''),
        reported_flags=None,
    )

    check_string_update(
        '"a\\"\\"\\"\\nb"',
        snapshot("""\
'''\\
a\"\"\"
b\\
'''\
"""),
        reported_flags=None,
    )

    check_string_update(
        '"a\\"\\"\\"\\n\\\'\\\'\\\'b"',
        snapshot('''\
"""\\
a\\"\\"\\"
\'\'\'b\\
"""\
'''),
        reported_flags=None,
    )

    check_string_update('b"a\\nb"', snapshot('b"a\\nb"'), reported_flags=set())

    check_string_update(
        '"\\n\\\'"',
        snapshot('''\
"""\\

'\\
"""\
'''),
        reported_flags=None,
    )

    check_string_update(
        '"\\n\\""',
        snapshot('''\
"""\\

"\\
"""\
'''),
        reported_flags=None,
    )

    check_string_update(
        "\"'''\\n\\\"\"",
        snapshot('''\
"""\\
\'\'\'
\\"\\
"""\
'''),
        reported_flags=None,
    )

    check_string_update(
        '"\\n\b"',
        snapshot('''\
"""\\

\\x08\\
"""\
'''),
        reported_flags=None,
    )


def check_string_update(string, expected_str=..., reported_flags={"update"}):
    prefix = "s = snapshot("
    suffix = ")"

    check_update(
        f"{prefix}{string}{suffix}\nassert {string} == s",
        flags="update",
        reported_flags=snapshot_arg(reported_flags),
        expected_code=Transformed(
            lambda v: v.split("assert")[0]
            .strip()
            .removeprefix(prefix)
            .removesuffix(suffix),
            expected_str,
        ),
    )


def test_string_quote_choice():
    check_string_update(
        "\" \\'\\'\\' \\'\\'\\' \\\"\\\"\\\"\\nother_line\"",
        snapshot('''\
"""\\
 \'\'\' \'\'\' \\"\\"\\"
other_line\\
"""\
'''),
        reported_flags=None,
    )

    check_string_update(
        '" \\\'\\\'\\\' \\"\\"\\" \\"\\"\\"\\nother_line"',
        snapshot("""\
'''\\
 \\'\\'\\' \"\"\" \"\"\"
other_line\\
'''\
"""),
        reported_flags=None,
    )

    check_string_update(
        '"\\n\\""',
        snapshot('''\
"""\\

"\\
"""\
'''),
        reported_flags=None,
    )

    check_string_update("'\\n'", snapshot("'\\n'"), reported_flags=set())
    check_string_update("'abc\\n'", snapshot("'abc\\n'"), reported_flags=set())

    check_string_update(
        "'abc\\nabc'",
        snapshot('''\
"""\\
abc
abc\\
"""\
'''),
        reported_flags=None,
    )

    check_string_update(
        "'\\nabc'",
        snapshot('''\
"""\\

abc\\
"""\
'''),
        reported_flags=None,
    )

    check_string_update(
        "'a\\na\\n'",
        snapshot('''\
"""\\
a
a
"""\
'''),
        reported_flags=None,
    )

    check_string_update(
        '''"""\\
a
"""''',
        snapshot('"a\\n"'),
        reported_flags=None,
    )


@given(s=text())
def test_string_convert(s):
    print(s)
    assert ast.literal_eval(triple_quote(s)) == s


def test_newline():
    Example("""\
from inline_snapshot import snapshot

def test_a():
    assert "a\\r\\nb" == snapshot()
""").run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot({"tests/test_something.py": '''\
from inline_snapshot import snapshot

def test_a():
    assert "a\\r\\nb" == snapshot("""\\
a\\r
b\\
""")
'''}),
    )


def test_trailing_whitespaces():
    Example("""\
from inline_snapshot import snapshot

def test_a():
    assert "a   \\r\\nb   \\nc   " == snapshot()
""").run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot({"tests/test_something.py": '''\
from inline_snapshot import snapshot

def test_a():
    assert "a   \\r\\nb   \\nc   " == snapshot("""\\
a   \\r
b   \\n\\
c   \\
""")
'''}),
    )


def test_fix_remove_triple_quotes():
    Example("""\
from inline_snapshot import snapshot

def test_a():
    assert "" == snapshot('''
a
b\
''')
""").run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot({"tests/test_something.py": """\
from inline_snapshot import snapshot

def test_a():
    assert "" == snapshot("")
"""}),
    )


def test_update_remove_triple_quotes():
    Example("""\
from inline_snapshot import snapshot

def test_a():
    assert "" == snapshot(\"\"\"\"\"\")
""").run_inline(
        ["--inline-snapshot=update"],
        changed_files=snapshot({"tests/test_something.py": """\
from inline_snapshot import snapshot

def test_a():
    assert "" == snapshot("")
"""}),
    )
