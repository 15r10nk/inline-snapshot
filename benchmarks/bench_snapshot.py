"""Warm-source comparisons: each result is a batch of ten assertions."""

from pathlib import Path
from tempfile import TemporaryDirectory

from inline_snapshot._global_state import snapshot_env

from ._fixtures import BATCH_SIZE
from ._fixtures import CASES
from ._fixtures import SUITE_VERSION
from ._fixtures import load_module
from ._fixtures import snapshot_functions
from ._fixtures import source


class Comparison:
    version = SUITE_VERSION
    params = [CASES, ["first", "repeated", "disabled", "plain"]]
    param_names = ["case", "mode"]
    # Setup must run before EVERY batch, including first-visit measurements.
    number = 1
    warmup_time = 0
    repeat = 10
    rounds = 2
    # Historical revisions can take seconds per large-schema assertion batch,
    # including the untimed cache warmup before each measurement.
    timeout = 300

    def setup(self, case, mode):
        self.load_workload(case)
        self.functions = snapshot_functions(self.module)
        self.context = snapshot_env()
        self.state = self.context.__enter__()
        assert self.state.active
        self.warm_source_caches()
        self.select_mode(mode)

    def load_workload(self, case):
        # Reuse the module across samples: unique filenames/code objects would
        # accumulate in executing's source caches and change memory pressure.
        # TemporaryDirectory removes the fixture when this worker exits.
        if not hasattr(self, "module"):
            self.directory = TemporaryDirectory()
            path = Path(self.directory.name) / "fixture.py"
            path.write_text(source(case), encoding="utf-8")
            self.module = load_module(path)

    def warm_source_caches(self):
        # Populate source/executing caches outside timing and check correctness.
        for function in self.functions:
            function()
        assert len(self.state.snapshots) == BATCH_SIZE
        assert all(
            ref._context.expr.node is not None for ref in self.state.snapshots.values()
        )
        assert not self.state.missing_values and not self.state.incorrect_values

    def select_mode(self, mode):
        if mode == "first":
            self.state.snapshots.clear()
        elif mode == "repeated":
            self.functions = [self.functions[0]] * BATCH_SIZE
        elif mode == "disabled":
            self.state.snapshots.clear()
            self.state.active = False
        elif mode == "plain":
            self.state.snapshots.clear()
            self.functions = [self.module.plain] * BATCH_SIZE

    def time_comparison(self, case, mode):
        for function in self.functions:
            function()

    def teardown(self, case, mode):
        try:
            assert not self.state.missing_values and not self.state.incorrect_values
            assert len(self.state.snapshots) == (
                BATCH_SIZE if mode in {"first", "repeated"} else 0
            )
        finally:
            self.context.__exit__(None, None, None)


class ModelComparison(Comparison):
    """Optional adapter workload, kept as a separate benchmark family."""

    params = [["models"], ["first", "repeated", "disabled", "plain"]]
