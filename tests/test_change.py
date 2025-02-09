import ast

import pytest
from executing import Source

from inline_snapshot._change import CallArg
from inline_snapshot._change import Delete
from inline_snapshot._change import Replace
from inline_snapshot._change import apply_all
from inline_snapshot._inline_snapshot import snapshot
from inline_snapshot._rewrite_code import ChangeRecorder
from inline_snapshot._source_file import SourceFile


@pytest.fixture
def check_change(tmp_path):
    i = 0

    def w(source, changes, new_code):
        nonlocal i

        filename = tmp_path / f"test_{i}.py"
        i += 1

        filename.write_text(source)
        print(f"\ntest: {source}")

        source = Source.for_filename(filename)
        module = source.tree
        context = SourceFile(source)

        call = module.body[0].value
        assert isinstance(call, ast.Call)

        cr = ChangeRecorder()
        apply_all(changes(context, call), cr)

        cr.virtual_write()

        cr.dump()

        assert list(cr.files())[0].source == new_code

    return w


def test_change_function_args(check_change):

    check_change(
        "f(a,b=2)",
        lambda source, call: [
            Replace(
                flag="fix",
                file=source,
                node=call.args[0],
                new_code="22",
                old_value=0,
                new_value=0,
            )
        ],
        snapshot("f(22,b=2)"),
    )

    check_change(
        "f(a,b=2)",
        lambda source, call: [
            Delete(
                flag="fix",
                file=source,
                node=call.args[0],
                old_value=0,
            )
        ],
        snapshot("f(b=2)"),
    )

    check_change(
        "f(a,b=2)",
        lambda source, call: [
            CallArg(
                flag="fix",
                file=source,
                node=call,
                arg_pos=0,
                arg_name=None,
                new_code="22",
                new_value=22,
            )
        ],
        snapshot("f(22, a,b=2)"),
    )
