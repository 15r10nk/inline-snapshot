import pytest

from inline_snapshot._inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


def test_list_adapter_create_inner_snapshot():

    Example("""\
from inline_snapshot import snapshot
from dirty_equals import IsInt

def test_list():

    assert [1,2,3,4] == snapshot([1,IsInt(),snapshot(),4]),"not equal"
""").run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot({"tests/test_something.py": """\
from inline_snapshot import snapshot
from dirty_equals import IsInt

def test_list():

    assert [1,2,3,4] == snapshot([1,IsInt(),snapshot(3),4]),"not equal"
"""}),
        raises=snapshot("<no exception>"),
    )


def test_list_adapter_fix_inner_snapshot():

    Example("""\
from inline_snapshot import snapshot
from dirty_equals import IsInt

def test_list():

    assert [1,2,3,4] == snapshot([1,IsInt(),snapshot(8),4]),"not equal"
""").run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot({"tests/test_something.py": """\
from inline_snapshot import snapshot
from dirty_equals import IsInt

def test_list():

    assert [1,2,3,4] == snapshot([1,IsInt(),snapshot(3),4]),"not equal"
"""}),
        raises=snapshot("<no exception>"),
    )


@pytest.mark.no_rewriting
def test_sequence_adapter_reeval(executing_used):

    Example("""\
from inline_snapshot import snapshot,Is

def test_list():

    for i in (1,2,3):
        assert [1,i] == snapshot([1,Is(i)]),"not equal"
        assert (1,i) == snapshot((1,Is(i))),"not equal"
""").run_inline(
        changed_files=snapshot({}),
        raises=snapshot("<no exception>"),
    )


def test_list_var():

    Example("""\
from inline_snapshot import snapshot,Is

def test_list():
    l=[1]
    assert l == snapshot(l), "not equal"
""").run_inline(
        ["--inline-snapshot=update"],
        changed_files=snapshot({"tests/test_something.py": """\
from inline_snapshot import snapshot,Is

def test_list():
    l=[1]
    assert l == snapshot([1]), "not equal"
"""}),
    )


def test_tuple_constructor():
    Example("""\
from inline_snapshot import snapshot

def test_tuple():
    snapshot(tuple()), "not equal"
""").run_inline(
        ["--inline-snapshot=fix"], changed_files=snapshot({}), reported_categories=set()
    )


def test_tuple_fix_shorter():
    """Tuple shrinks: surplus old elements are deleted, paired elements fixed.
    Expressions in paired positions are preserved."""
    Example("""\
from inline_snapshot import snapshot

def test_tuple():
    assert (1, 5) == snapshot((0+1, 2, 3, 4, 5))
""").run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot({"tests/test_something.py": """\
from inline_snapshot import snapshot

def test_tuple():
    assert (1, 5) == snapshot((0+1, 5))
"""}),
    )


def test_tuple_fix_longer():
    """Tuple grows: paired elements are fixed, extra new elements are inserted."""
    Example("""\
from inline_snapshot import snapshot

def test_tuple():
    assert (1, 2, 3, 4, 5, 6) == snapshot((0+1, 3))
""").run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot({"tests/test_something.py": """\
from inline_snapshot import snapshot

def test_tuple():
    assert (1, 2, 3, 4, 5, 6) == snapshot((0+1, 2, 3, 4, 5, 6))
"""}),
    )


def test_tuple_update_preserves_expression():
    """Tuple update: elements whose values haven't changed keep their original
    expression (e.g. ``2+2`` is not rewritten to ``4``)."""
    Example("""\
from inline_snapshot import snapshot

def test_tuple():
    assert (4, 99) == snapshot((2+2, 1+1))
""").run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot({"tests/test_something.py": """\
from inline_snapshot import snapshot

def test_tuple():
    assert (4, 99) == snapshot((2+2, 99))
"""}),
    )
