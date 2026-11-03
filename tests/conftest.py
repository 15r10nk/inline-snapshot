import sys
import textwrap
from contextlib import contextmanager

import executing
import pytest
from dirty_equals import AnyThing

from inline_snapshot._snapshot_arg import snapshot_arg
from inline_snapshot.testing._example import Example

pytest_plugins = "pytester"


pytest.register_assert_rewrite("tests.example")


@pytest.fixture(autouse=True)
def check_pypy(request):
    implementation = sys.implementation.name
    node = request.node

    if implementation != "cpython" and node.get_closest_marker("no_rewriting") is None:
        pytest.skip(f"{implementation} is not supported")

    yield


def check_update(
    source_code,
    *,
    flags="",
    reported_flags=None,
    expected_code=...,
    raises="<no exception>",
    context_managers=(),
):
    e = Example(
        {
            "pyproject.toml": """\
[tool.inline-snapshot]
show-updates=true""",
            "test_a.py": f"""\
from inline_snapshot import snapshot,outsource

def test_a():
    exec(compile(open("source_code.py").read(),"source_code.py","exec"))
""",
            "source_code.py": source_code,
        }
    )
    # assert snapshot_arg(source_code)==textwrap.dedent(source_code).strip()

    result = e.run_inline(
        [f"--inline-snapshot={flags}"],
        context_managers=context_managers,
        reported_categories=snapshot_arg(reported_flags),
        changed_files=AnyThing(),
        raises=snapshot_arg(raises),
    )

    assert (
        snapshot_arg(expected_code)
        == textwrap.dedent(
            result.read_file("source_code.py").split("# split")[-1]
        ).strip()
    )


@contextmanager
def no_executing_context():
    real_executing = executing.Source.executing

    def fake_executing(frame):
        result = real_executing(frame)
        result.node = None
        return result

    from unittest.mock import patch

    with patch.object(executing.Source, "executing", fake_executing):
        # monkeypatch.setattr(executing.Source, "executing", fake_executing)
        yield


@pytest.fixture(params=[True, False], ids=["executing", "without-executing"])
def executing_used(request):
    return ExecutingContext(request.param)


class ExecutingContext:
    def __init__(self, used):
        self.used = used
        self.context = None

    def __bool__(self):
        return self.used

    def __enter__(self):
        if not self.used:
            self.context = no_executing_context()
            self.context.__enter__()
        return self

    def __exit__(self, *args):
        if self.context is not None:
            context = self.context
            self.context = None
            return context.__exit__(*args)
        return None
