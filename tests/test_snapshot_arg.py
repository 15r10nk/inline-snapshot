"""Tests for snapshot_arg() covering previously uncovered code paths."""

from inline_snapshot import snapshot
from inline_snapshot.testing import Example
from tests.conftest import no_executing_context


def test_snapshot_arg_no_comparison():
    """_node is None and _new_value is CustomUndefined: _changes() returns early (line 168)."""
    Example(
        """\
from inline_snapshot._snapshot_arg import snapshot_arg

def check_value(x, expected=...):
    snapshot_arg(expected)  # called but never compared

def test_a():
    check_value(5)  # expected not passed -> _node is None
"""
    ).run_inline(
        ["--inline-snapshot=create"],
    )


def test_snapshot_arg_create_positional():
    """Arg passed positionally: node = call_node.args[arg_pos] (line 133)."""
    Example(
        """\
from inline_snapshot._snapshot_arg import snapshot_arg

def check_value(x, expected=...):
    assert x == snapshot_arg(expected)

def test_a():
    check_value(5, ...)
"""
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot._snapshot_arg import snapshot_arg

def check_value(x, expected=...):
    assert x == snapshot_arg(expected)

def test_a():
    check_value(5, 5)
"""
            }
        ),
    )


def test_snapshot_arg_default_value():
    """Arg passed positionally: node = call_node.args[arg_pos] (line 133)."""
    Example(
        """\
from inline_snapshot._snapshot_arg import snapshot_arg

def check_value(x, expected=8):
    assert x == snapshot_arg(expected)

def test_a():
    check_value(8, 5)
    check_value(8)
    check_value(8,8)
"""
    ).run_inline(
        ["--inline-snapshot=fix,create"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot._snapshot_arg import snapshot_arg

def check_value(x, expected=8):
    assert x == snapshot_arg(expected)

def test_a():
    check_value(8)
    check_value(8)
    check_value(8)
"""
            }
        ),
    )


def test_snapshot_kw_only_arg_default_value():
    """Arg passed positionally: node = call_node.args[arg_pos] (line 133)."""
    Example(
        """\
from inline_snapshot._snapshot_arg import snapshot_arg

def check_value(x,*, other=5, expected=8):
    assert x == snapshot_arg(expected)

def test_a():
    check_value(8, expected=5)
    check_value(8)
    check_value(8,expected=8)
"""
    ).run_inline(
        ["--inline-snapshot=fix,create"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot._snapshot_arg import snapshot_arg

def check_value(x,*, other=5, expected=8):
    assert x == snapshot_arg(expected)

def test_a():
    check_value(8)
    check_value(8)
    check_value(8)
"""
            }
        ),
    )


def test_snapshot_no_argument():
    """Arg passed positionally: node = call_node.args[arg_pos] (line 133)."""
    Example(
        """\
from inline_snapshot._snapshot_arg import snapshot_arg

def check_value(x):
    expected=8
    assert x == snapshot_arg(expected)

def test_a():
    check_value(8)
"""
    ).run_inline(
        ["--inline-snapshot=fix,create"],
        changed_files=snapshot({}),
        raises=snapshot(
            """\
UsageError:
the argument of snapshot_arg(...) has to be an argument of the calling function\
"""
        ),
    )


def test_snapshot_no_default():
    """Arg passed positionally: node = call_node.args[arg_pos] (line 133)."""
    Example(
        """\
from inline_snapshot._snapshot_arg import snapshot_arg

def check_value(x,expected):
    assert x == snapshot_arg(expected)

def test_a():
    check_value(8,5)
"""
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot._snapshot_arg import snapshot_arg

def check_value(x,expected):
    assert x == snapshot_arg(expected)

def test_a():
    check_value(8,8)
"""
            }
        ),
    )


def test_snapshot_as_argument():
    """Arg passed positionally: node = call_node.args[arg_pos] (line 133)."""
    Example(
        """\
from inline_snapshot._snapshot_arg import snapshot_arg
from inline_snapshot import snapshot

def check_value(x,expected):
    assert x == snapshot_arg(expected)

def test_a():
    check_value(8,snapshot(5))
"""
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot._snapshot_arg import snapshot_arg
from inline_snapshot import snapshot

def check_value(x,expected):
    assert x == snapshot_arg(expected)

def test_a():
    check_value(8,snapshot(8))
"""
            }
        ),
    )


def test_snapshot_arg_fix_positional():
    """Fix a snapshot passed positionally: line 133 + line 184."""
    Example(
        """\
from inline_snapshot._snapshot_arg import snapshot_arg

def check_value(x, expected=5):
    assert x == snapshot_arg(expected)

def test_a():
    check_value(6, 5)
"""
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot._snapshot_arg import snapshot_arg

def check_value(x, expected=5):
    assert x == snapshot_arg(expected)

def test_a():
    check_value(6, 6)
"""
            }
        ),
    )


def test_snapshot_arg_fix_keyword():
    """Arg passed as keyword: lines 136-137 + line 184."""
    Example(
        """\
from inline_snapshot._snapshot_arg import snapshot_arg

def check_value(x, expected=...,as_str=...):
    assert x == snapshot_arg(expected)
    assert str(x) == snapshot_arg(as_str)

def test_a():
    check_value(6, expected=5,as_str="a")
"""
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot._snapshot_arg import snapshot_arg

def check_value(x, expected=...,as_str=...):
    assert x == snapshot_arg(expected)
    assert str(x) == snapshot_arg(as_str)

def test_a():
    check_value(6, expected=6,as_str="6")
"""
            }
        ),
    )


def test_snapshot_arg_re_eval():
    """Same call site hit twice in a loop: triggers _re_eval (lines 187-189)."""
    Example(
        """\
from inline_snapshot._snapshot_arg import snapshot_arg

def check_value(x, expected=...):
    snapshot_arg(expected)  # no comparison, just trigger the re-eval path

def test_a():
    for v in [1, 2]:
        check_value(v)
"""
    ).run_inline(
        ["--inline-snapshot=create"],
    )


def test_snapshot_arg_wrong_arg_type():
    """Non-Name argument (attribute access): raises UsageError (line 91)."""
    Example(
        """\
from inline_snapshot._snapshot_arg import snapshot_arg

class Obj:
    val = 5

def my_func(x):
    assert 5 == snapshot_arg(x.val)

def test_a():
    my_func(Obj())
"""
    ).run_inline(
        ["--inline-snapshot=create"],
        raises=snapshot(
            """\
UsageError:
snapshot_arg() can only be called with function argument of the calling function as argument\
"""
        ),
    )


def test_snapshot_arg_disable():
    Example(
        """\
from inline_snapshot._snapshot_arg import snapshot_arg


def my_func(x):
    s= snapshot_arg(x)
    assert isinstance(s,int)
    assert s==2

def test_a():
    my_func(2)
"""
    ).run_inline(
        ["--inline-snapshot=disable"],
    )


def test_snapshot_arg_module_level():
    """snapshot_arg called at module level: raises UsageError (line 116)."""
    Example(
        """\
from inline_snapshot._snapshot_arg import snapshot_arg

x = 5
y = snapshot_arg(x)

def test_a():
    pass
"""
    ).run_inline(
        ["--inline-snapshot=create"],
        raises=snapshot(
            """\
UsageError:
snapshot_arg() can only be used inside functions\
"""
        ),
    )


def test_without_executing():
    Example(
        """\
from inline_snapshot._snapshot_arg import snapshot_arg

def check_value(x, expected=...):
    assert x == snapshot_arg(expected)

def test_a():
    check_value(5, expected=8)
"""
    ).run_inline(
        ["--inline-snapshot=short-report"],
        context_managers=[no_executing_context()],
        report=snapshot(
            """\
FAIL: some snapshots in this test have incorrect values.
If you just created this value with --inline-snapshot=create, the value is now \n\
created and you can ignore this message.


═══════════════════════════════ inline-snapshot ════════════════════════════════
Error: one snapshot is missing a value (--inline-snapshot=create)

You can also use --inline-snapshot=review to approve the changes interactively
"""
        ),
        raises=snapshot("AssertionError:\n"),
    )
