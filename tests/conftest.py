import sys
import textwrap

import black
import executing
import pytest

from inline_snapshot._get_snapshot_value import get_snapshot_value
from inline_snapshot._snapshot_arg import snapshot_arg
from inline_snapshot.testing._example import Example
from tests.utils import Store

pytest_plugins = "pytester"


pytest.register_assert_rewrite("tests.example")

black.files.find_project_root = black.files.find_project_root.__wrapped__  # type: ignore


@pytest.fixture(autouse=True)
def check_pypy(request):
    implementation = sys.implementation.name
    node = request.node

    if implementation != "cpython" and node.get_closest_marker("no_rewriting") is None:
        pytest.skip(f"{implementation} is not supported")

    yield


def check_update(source_code, *, flags="", reported_flags=None, expected_code=...):
    code = f"""\
from inline_snapshot import snapshot,outsource

def test_a():
    exec(compile(open("source_code.py").read(),"source_code.py","exec"))
"""
    e = Example(
        {
            "pyproject.toml": """\
[tool.inline-snapshot]
show-updates=true""",
            "test_a.py": code,
            "source_code.py": textwrap.dedent(source_code),
        }
    )
    result = e.run_inline(
        [f"--inline-snapshot={flags}"],
        reported_categories=(result_flags := Store()),
    )

    flags_set = {*flags.split(",")} - {""}

    if get_snapshot_value(reported_flags):
        reported_flags_set = {*get_snapshot_value(reported_flags).split(",")} - {""}
    else:
        reported_flags_set = flags_set

    if reported_flags_set != set(result_flags.value):
        assert snapshot_arg(reported_flags) == ",".join(sorted(result_flags.value))

    assert (
        snapshot_arg(expected_code)
        == textwrap.dedent(
            result.read_file("source_code.py").split("# split")[-1]
        ).strip()
    )


@pytest.fixture(params=[True, False], ids=["executing", "without-executing"])
def executing_used(request, monkeypatch):
    used = request.param
    if used:
        yield used
    else:
        real_executing = executing.Source.executing

        def fake_executing(frame):
            result = real_executing(frame)
            result.node = None
            return result

        monkeypatch.setattr(executing.Source, "executing", fake_executing)
        yield used
