import pytest

from benchmarks._fixtures import CASES
from benchmarks._fixtures import expand_call_sites
from benchmarks._fixtures import load_module
from benchmarks._fixtures import source
from inline_snapshot._global_state import snapshot_env


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
