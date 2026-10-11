"""Fresh-process pytest timings, including startup, reporting and source edits."""

import ast
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from ._fixtures import BATCH_SIZE
from ._fixtures import SUITE_VERSION
from ._fixtures import pytest_source
from ._fixtures import snapshot_functions


class PytestSession:
    version = SUITE_VERSION
    params = ["active", "disabled", "create", "fix", "update"]
    param_names = ["mode"]
    number = 1
    warmup_time = 0
    repeat = 3
    rounds = 2
    timeout = 120

    def setup(self, mode):
        self.directory = TemporaryDirectory()
        self.root = Path(self.directory.name)
        # Ignore user/project pytest settings and explicitly enable our plugin.
        (self.root / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
        self.path = self.root / "test_workload.py"
        self.original = pytest_source(mode)
        self.path.write_text(self.original, encoding="utf-8")
        (self.root / "conftest.py").write_text(
            "from inline_snapshot._global_state import state\n"
            "def pytest_sessionfinish(session):\n"
            f"    assert state().active is {mode != 'disabled'}\n",
            encoding="utf-8",
        )
        self.env = dict(os.environ)
        for key in (
            "PYTEST_ADDOPTS",
            "PYTEST_PLUGINS",
            "PYTHONPATH",
            "INLINE_SNAPSHOT_DEFAULT_FLAGS",
        ):
            self.env.pop(key, None)
        self.env.update(
            PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
            PYTHONHASHSEED="0",
            COLUMNS="100",
            NO_COLOR="1",
        )
        flag = (
            "short-report"
            if mode == "active"
            else "disable" if mode == "disabled" else mode
        )
        self.command = [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "inline_snapshot.pytest_plugin",
            "-c",
            "pytest.ini",
            "--color=no",
            "-q",
            f"--inline-snapshot={flag}",
        ]

    def time_session(self, mode):
        self.result = subprocess.run(
            self.command,
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def teardown(self, mode):
        try:
            result = self.result
            output = result.stdout + result.stderr
            # Creation/fixing deliberately reports the original failing tests.
            assert result.returncode == (1 if mode in {"create", "fix"} else 0), output
            assert f"{BATCH_SIZE} passed" in output, output
            if mode in {"create", "fix"}:
                assert f"{BATCH_SIZE} errors" in output, output
            rewritten = self.path.read_text(encoding="utf-8")
            changed = rewritten != self.original
            assert changed == (mode in {"create", "fix", "update"}), output
            if mode == "update":
                values = [
                    ast.literal_eval(node.args[0])
                    for node in ast.walk(ast.parse(rewritten))
                    if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "snapshot"
                ]
                assert values == [[1, 2, 3]] * BATCH_SIZE, output
                # Equality alone accepts floats and misses incomplete updates.
                assert all(
                    type(item) is int for value in values for item in value
                ), output
            if changed:
                # A fast no-rewriting check validates the resulting expected values.
                from inline_snapshot._global_state import snapshot_env

                from ._fixtures import load_module

                with snapshot_env() as state:
                    state.active = False
                    module = load_module(self.path)
                    for function in snapshot_functions(module):
                        function()
        finally:
            self.directory.cleanup()
