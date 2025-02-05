import pytest

from inline_snapshot._inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


@pytest.mark.xfail
def test_dirty_equals_repr():
    Example(
        """\
from inline_snapshot import snapshot
from dirty_equals import IsStr

def test_something():
    assert [IsStr()] == snapshot()
    """
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot({}),
        raises=snapshot(
            """\
UsageError:
inline-snapshot uses `copy.deepcopy` to copy objects,
but the copied object is not equal to the original one:

original: [HasRepr(IsStr, '< type(obj) can not be compared with == >')]
copied:   [HasRepr(IsStr, '< type(obj) can not be compared with == >')]

Please fix the way your object is copied or your __eq__ implementation.
"""
        ),
    )


def test_compare_dirty_equals_twice() -> None:

    Example(
        """
from dirty_equals import IsStr
from inline_snapshot import snapshot

def test():
    for x in 'ab':
        assert x == snapshot(IsStr())
        assert [x,5] == snapshot([IsStr(),3])
        assert {'a':x,'b':5} == snapshot({'a':IsStr(),'b':3})

"""
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "test_something.py": """\

from dirty_equals import IsStr
from inline_snapshot import snapshot

def test():
    for x in 'ab':
        assert x == snapshot(IsStr())
        assert [x,5] == snapshot([IsStr(),5])
        assert {'a':x,'b':5} == snapshot({'a':IsStr(),'b':5})

"""
            }
        ),
    )


def test_dirty_equals_in_unused_snapshot() -> None:

    Example(
        """
from dirty_equals import IsStr
from inline_snapshot import snapshot,Is

snapshot([IsStr(),3])
snapshot((IsStr(),3))
snapshot({1:IsStr(),2:3})
snapshot({1+1:2})

t=(1,2)
d={1:2}
l=[1,2]
snapshot([Is(t),Is(d),Is(l)])

def test():
    pass

"""
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot({}),
    )


def test_now_like_dirty_equals():
    # test for cases like https://github.com/15r10nk/inline-snapshot/issues/116

    Example(
        """
from dirty_equals import DirtyEquals
from inline_snapshot import snapshot


def test_time():

    now = 5

    class Now(DirtyEquals):
        def equals(self, other):
            return other == now

    assert 5 == snapshot(Now())

    now = 6

    assert 5 == snapshot(Now()), "different time"
"""
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot({}),
        raises=snapshot(
            """\
AssertionError:
different time\
"""
        ),
    )


def test_dirty_equals_with_changing_args() -> None:

    Example(
        """\
from dirty_equals import IsInt
from inline_snapshot import snapshot

def test_number():

    for i in range(5):
        assert ["a",i] == snapshot(["e",IsInt(gt=i-1,lt=i+1)])

"""
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from dirty_equals import IsInt
from inline_snapshot import snapshot

def test_number():

    for i in range(5):
        assert ["a",i] == snapshot(["a",IsInt(gt=i-1,lt=i+1)])

"""
            }
        ),
    )
