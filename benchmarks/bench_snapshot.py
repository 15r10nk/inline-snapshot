"""First-use comparisons in a fresh process for every measured batch."""

import sys
import types
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent

from ._fixtures import CASES
from ._fixtures import SUITE_VERSION


def retained_size(root):
    """Return the recursive size of state owned by ``root``.

    Frames expose their local values separately from ordinary instance state.
    Classes, functions, and modules are shared rather than owned and are not
    followed.
    """
    pending = [root]
    seen = set()
    total = 0
    while pending:
        value = pending.pop()
        if id(value) in seen:
            continue
        seen.add(id(value))
        total += sys.getsizeof(value)

        if isinstance(value, types.FrameType):
            pending.extend(value.f_locals.values())
        elif isinstance(value, dict):
            pending.extend(value.keys())
            pending.extend(value.values())
        elif isinstance(value, (list, tuple, set, frozenset)):
            pending.extend(value)
        elif not isinstance(
            value,
            (
                str,
                bytes,
                int,
                float,
                complex,
                type,
                types.FunctionType,
                types.MethodType,
                types.ModuleType,
            ),
        ):
            pending.extend(vars(value).values() if hasattr(value, "__dict__") else ())
    return total


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
                data.file is not None and data.operation is not None
                for data in state.snapshots.values()
            )
            """)
        return statement, setup


class ModelComparison(Comparison):
    """Optional adapter workload, kept as a separate benchmark family."""

    params = [["models"], ["active", "disabled", "plain"]]


class RetainedSnapshotState:
    """Memory retained by the session registry after snapshot evaluation."""

    version = SUITE_VERSION
    params = ["scalar"]
    param_names = ["case"]
    number = 1
    repeat = 3
    timeout = 300
    unit = "byte"
    call_site_count = 100
    frame_payload_size = 100_000

    def setup(self, case):
        from inline_snapshot._global_state import snapshot_env

        from ._fixtures import load_module
        from ._fixtures import source

        self.directory = TemporaryDirectory()
        path = Path(self.directory.name) / "fixture.py"
        workload = source(case, count=self.call_site_count)
        workload = workload.replace(
            "):\n",
            f"):\n    frame_payload = bytearray({self.frame_payload_size})\n",
        )
        path.write_text(workload, encoding="utf-8")
        self.module = load_module(path)
        self.context = snapshot_env()
        self.state = self.context.__enter__()
        for index in range(self.call_site_count):
            getattr(self.module, f"test_snapshot_{index}")()

    def track_retained_snapshots(self, case):
        return retained_size(self.state.snapshots)

    def teardown(self, case):
        self.context.__exit__(None, None, None)
        self.directory.cleanup()
