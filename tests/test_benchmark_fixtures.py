import subprocess
import sys
from contextlib import nullcontext

import pytest

from benchmarks._fixtures import CASES
from benchmarks._fixtures import expand_call_sites
from benchmarks._fixtures import load_module
from benchmarks._fixtures import source
from benchmarks.bench_pytest import PytestSession
from benchmarks.bench_snapshot import Comparison
from inline_snapshot._global_state import snapshot_env


@pytest.mark.parametrize("rewritten_count", [0, 1, 10])
def test_update_validation(rewritten_count):
    benchmark = PytestSession()
    benchmark.setup("update")
    rewritten = benchmark.original.replace(
        "snapshot([1.0, 2.0, 3.0])", "snapshot([1, 2, 3])", rewritten_count
    )
    benchmark.path.write_text(rewritten + "\n# unrelated edit\n", encoding="utf-8")
    benchmark.result = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="10 passed", stderr=""
    )
    with pytest.raises(AssertionError) if rewritten_count < 10 else nullcontext():
        benchmark.teardown("update")


def test_expanded_call_sites(tmp_path):
    path = tmp_path / "workload.py"
    path.write_text(
        expand_call_sites(
            """\
from inline_snapshot import snapshot

ACTUAL = {"items": [1, 2]}

def test_snapshot():
    # Keep literal syntax and comments intact.
    assert ACTUAL == snapshot({
        "items": [1, 2],
    })

def plain():
    assert ACTUAL == {"items": [1, 2]}
""",
            count=3,
        ),
        encoding="utf-8",
    )
    module = load_module(path)
    with snapshot_env() as state:
        for _ in range(2):
            for i in range(3):
                getattr(module, f"test_snapshot_{i}")()
            # First visits initialize distinct sites; repeated visits reuse them.
            assert len(state.snapshots) == 3
        nodes = [ref._context.expr.node for ref in state.snapshots.values()]
        assert all(node is not None for node in nodes)
        assert len({node.lineno for node in nodes}) == 3
        assert not state.missing_values and not state.incorrect_values
    module.plain()
    assert path.read_text().count("# Keep literal syntax and comments intact.") == 3


@pytest.mark.parametrize("case", CASES + ["models"])
def test_comparison_baseline(tmp_path, case):
    path = tmp_path / "workload.py"
    path.write_text(source(case, count=1), encoding="utf-8")
    module = load_module(path)
    with snapshot_env() as state:
        state.active = False
        module.test_snapshot_0()
        module.plain()
    if case == "text":
        assert module.ACTUAL not in (None, "")
        expected = next(
            value
            for value in module.test_snapshot_0.__code__.co_consts
            if isinstance(value, str)
        )
        assert module.ACTUAL == expected
        assert module.ACTUAL is not expected


@pytest.mark.parametrize("mode", ["active", "disabled", "plain"])
def test_cold_comparison(mode):
    statement, setup = Comparison().timeraw_comparison("schema", mode)
    # Run the generated program in a fresh interpreter, as ASV timeraw does.
    # Setup must not execute snapshots, and each selected call runs once.
    guard = """
import inline_snapshot
original_snapshot = inline_snapshot.snapshot
def unexpected_snapshot(*args, **kwargs):
    raise AssertionError("Setup must not execute snapshot assertions")
inline_snapshot.snapshot = unexpected_snapshot
"""
    checks = """
inline_snapshot.snapshot = original_snapshot
module.snapshot = original_snapshot
assert not state.snapshots
assert not state.missing_values and not state.incorrect_values
calls = []
original_functions = functions
def record(function):
    def wrapped():
        calls.append(function)
        return function()
    return wrapped
functions = [record(function) for function in functions]
"""
    validation = f"""
assert calls == original_functions
assert len(calls) == BATCH_SIZE
assert len(set(calls)) == {1 if mode == "plain" else 10}
assert state.active is {mode != "disabled"}
"""
    result = subprocess.run(
        [sys.executable, "-c", guard + setup + checks + statement + validation],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
