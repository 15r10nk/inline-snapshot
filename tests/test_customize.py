import textwrap

import pytest

from inline_snapshot import snapshot
from inline_snapshot.testing import Example


@pytest.mark.parametrize(
    "original,flag", [("'a'", "update"), ("'b'", "fix"), ("", "create")]
)
def test_custom_dirty_equal(original, flag):

    Example(
        {
            "tests/conftest.py": """\
from inline_snapshot import customize
from inline_snapshot import Builder
from dirty_equals import IsStr

@customize
def re_handler(value, builder: Builder):
    if value == IsStr(regex="[a-z]"):
        return builder.create_call(IsStr, [], {"regex": "[a-z]"})
""",
            "tests/test_something.py": f"""\
from inline_snapshot import snapshot

def test_a():
    assert snapshot({original}) == "a"
""",
        }
    ).run_inline(
        [f"--inline-snapshot={flag}"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot

from dirty_equals import IsStr

def test_a():
    assert snapshot(IsStr(regex="[a-z]")) == "a"
"""
            }
        ),
    )


@pytest.mark.parametrize(
    "original,flag",
    [("{'1': 1, '2': 2}", "update"), ("5", "fix"), ("", "create")],
)
def test_create_imports(original, flag):

    Example(
        {
            "tests/test_something.py": f"""\
from inline_snapshot import snapshot

def counter():
    from collections import Counter
    return Counter("122")

def test():
    assert counter() == snapshot({original})
"""
        }
    ).run_inline(
        [f"--inline-snapshot={flag}"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot

from collections import Counter

def counter():
    from collections import Counter
    return Counter("122")

def test():
    assert counter() == snapshot(Counter({"1": 1, "2": 2}))
"""
            }
        ),
    )


def test_snapshot_value():
    conftest = textwrap.dedent(
        """
        from inline_snapshot import customize
        from inline_snapshot import Builder
        from dirty_equals import IsStr

        @customize
        def str_handler(value, builder: Builder, snapshot_value):
            if snapshot_value == "IsStr":
               return builder.create_call(IsStr)
        """
    )

    before = textwrap.dedent(
        """
        from inline_snapshot import snapshot

        def test():
            assert snapshot("IsStr") == "Hello, world!"
        """
    )

    Example(
        {
            "tests/test_something.py": before,
            "tests/conftest.py": conftest,
        }
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\

from inline_snapshot import snapshot

from dirty_equals import IsStr

def test():
    assert snapshot(IsStr()) == "Hello, world!"
"""
            }
        ),
    )
