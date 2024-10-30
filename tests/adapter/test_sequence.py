from inline_snapshot._inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


def test_list_adapter_create_inner_snapshot():

    Example(
        """\
from inline_snapshot import snapshot
from dirty_equals import IsInt

def test_list():

    assert [1,2,3,4] == snapshot([1,IsInt(),snapshot(),4]),"not equal"
"""
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from inline_snapshot import snapshot
from dirty_equals import IsInt

def test_list():

    assert [1,2,3,4] == snapshot([1,IsInt(),snapshot(3),4]),"not equal"
"""
            }
        ),
        raises=snapshot(
            """\
AssertionError:
not equal\
"""
        ),
    )


def test_list_adapter_fix_inner_snapshot():

    Example(
        """\
from inline_snapshot import snapshot
from dirty_equals import IsInt

def test_list():

    assert [1,2,3,4] == snapshot([1,IsInt(),snapshot(8),4]),"not equal"
"""
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from inline_snapshot import snapshot
from dirty_equals import IsInt

def test_list():

    assert [1,2,3,4] == snapshot([1,IsInt(),snapshot(3),4]),"not equal"
"""
            }
        ),
        raises=snapshot(
            """\
AssertionError:
not equal\
"""
        ),
    )
