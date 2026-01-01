import pytest

from inline_snapshot import snapshot
from inline_snapshot._customize import customize
from inline_snapshot.extra import raises
from inline_snapshot.testing import Example


@pytest.mark.parametrize(
    "original,flag", [("'a'", "update"), ("'b'", "fix"), ("", "create")]
)
def test_custom_dirty_equal(original, flag):

    Example(
        f"""\
from inline_snapshot import customize
from inline_snapshot import Builder
from inline_snapshot import snapshot
from dirty_equals import IsStr

@customize
def re_handler(value, builder: Builder):
    if value == IsStr(regex="[a-z]"):
        return builder.create_call(IsStr, [], {{"regex": "[a-z]"}})

def test_a():
    assert snapshot({original}) == "a"
"""
    ).run_inline(
        [f"--inline-snapshot={flag}"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import customize
from inline_snapshot import Builder
from inline_snapshot import snapshot
from dirty_equals import IsStr

@customize
def re_handler(value, builder: Builder):
    if value == IsStr(regex="[a-z]"):
        return builder.create_call(IsStr, [], {"regex": "[a-z]"})

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


def test_customize_argument_exceptions():

    with raises(
        snapshot("UsageError: `value` has a default value which is not supported")
    ):

        @customize
        def f(value=5):
            pass

    with raises(
        snapshot(
            "UsageError: `value` is not a positional or keyword parameter, which is not supported"
        )
    ):

        @customize
        def f(value, /):
            pass

    with raises(
        snapshot(
            "UsageError: `value` is not a positional or keyword parameter, which is not supported"
        )
    ):

        @customize
        def f(*, value):
            pass

    with raises(
        snapshot(
            "UsageError: `my_own_arg` is an unknown parameter. allowed are ['builder', 'global_vars', 'local_vars', 'value']"
        )
    ):

        @customize
        def f(my_own_arg):
            pass
