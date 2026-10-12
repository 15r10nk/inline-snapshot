"""First-use comparisons in a fresh process for every measured batch."""

from pathlib import Path
from textwrap import dedent

from ._fixtures import CASES
from ._fixtures import SUITE_VERSION


class Comparison:
    version = SUITE_VERSION
    params = [CASES, ["active", "disabled", "plain"]]
    param_names = ["case", "mode"]
    # Each timeraw sample starts a new process and executes the batch once.
    number = 1
    warmup_time = 0
    repeat = 10
    rounds = 2
    timeout = 300

    def timeraw_comparison(self, case, mode):
        setup = dedent(f"""\
            import atexit
            import sys
            from pathlib import Path
            from tempfile import TemporaryDirectory

            sys.path.insert(0, {str(Path(__file__).resolve().parent.parent)!r})
            from benchmarks._fixtures import BATCH_SIZE, load_module, snapshot_functions, source
            from inline_snapshot._global_state import snapshot_env

            directory = TemporaryDirectory()
            atexit.register(directory.cleanup)
            path = Path(directory.name) / "fixture.py"
            path.write_text(source({case!r}), encoding="utf-8")
            module = load_module(path)
            context = snapshot_env()
            state = context.__enter__()
            atexit.register(context.__exit__, None, None, None)
            state.active = {mode != 'disabled'}
            functions = (
                [module.plain] * BATCH_SIZE
                if {mode == 'plain'} else snapshot_functions(module)
            )
            """)
        statement = dedent(f"""\
            for function in functions:
                function()
            assert not state.missing_values and not state.incorrect_values
            assert len(state.snapshots) == {'BATCH_SIZE' if mode == 'active' else '0'}
            assert all(
                ref._context.expr.node is not None
                for ref in state.snapshots.values()
            )
            """)
        return statement, setup


class ModelComparison(Comparison):
    """Optional adapter workload, kept as a separate benchmark family."""

    params = [["models"], ["active", "disabled", "plain"]]
