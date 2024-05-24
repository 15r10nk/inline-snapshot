from __future__ import annotations

import os
import platform
import re
import subprocess as sp
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import inline_snapshot._external
from .utils import snapshot_env
from inline_snapshot import _inline_snapshot
from inline_snapshot._inline_snapshot import Flags
from inline_snapshot._rewrite_code import ChangeRecorder

pytest_plugins = "pytester"


ansi_escape = re.compile(
    r"""
    \x1B  # ESC
    (?:   # 7-bit C1 Fe (except CSI)
        [@-Z\\-_]
    |     # or [ for CSI, followed by a control sequence
        \[
        [0-?]*  # Parameter bytes
        [ -/]*  # Intermediate bytes
        [@-~]   # Final byte
    )
""",
    re.VERBOSE,
)


class Example:
    def __init__(self, files):
        if isinstance(files, str):
            files = {"test_something.py": files}

        self.files = files

    def write_files(self, dir: Path):
        for name, content in self.files.items():
            (dir / name).write_text(content)

    def read_files(self, dir: Path):
        return {p.name: p.read_text() for p in dir.iterdir() if p.is_file()}

    def run_inline(
        self, *flags, changes=None, reported_flags=None, changed_files=None
    ) -> Example:

        with TemporaryDirectory() as dir:
            tmp_path = Path(dir)

            self.write_files(tmp_path)

            with snapshot_env():
                with ChangeRecorder().activate() as recorder:
                    _inline_snapshot._update_flags = Flags({*flags})
                    inline_snapshot._external.storage = (
                        inline_snapshot._external.DiscStorage(tmp_path / ".storage")
                    )

                    error = False

                    try:
                        for filename in tmp_path.glob("*.py"):
                            globals: dict[str, Any] = {}
                            exec(
                                compile(filename.read_text("utf-8"), filename, "exec"),
                                globals,
                            )

                            # run all test_* functions
                            for k, v in globals.items():
                                if k.startswith("test_") and callable(v):
                                    v()

                    finally:
                        _inline_snapshot._active = False

                    # number_snapshots = len(_inline_snapshot.snapshots)

                    snapshot_flags = set()

                    all_changes = []

                    for snapshot in _inline_snapshot.snapshots.values():
                        snapshot_flags |= snapshot._flags
                        snapshot._change()
                        all_changes += snapshot._changes()

                    if reported_flags is not None:
                        assert sorted(snapshot_flags) == reported_flags

                    if changes is not None:
                        assert [c for c in all_changes] == changes

                    recorder.fix_all()

            if changed_files is not None:
                current_files = {}

                for name, content in sorted(self.read_files(tmp_path).items()):
                    if name not in self.files or self.files[name] != content:
                        current_files[name] = content
                assert changed_files == current_files

            return Example(self.read_files(tmp_path))

    def run_pytest(
        self, *args, changed_files=None, report=None, env={}, returncode=None
    ) -> Example:
        with TemporaryDirectory() as dir:
            tmp_path = Path(dir)
            self.write_files(tmp_path)

            cmd = ["pytest", *args]

            term_columns = 80

            command_env = dict(os.environ)
            command_env["TERM"] = "unknown"
            command_env["COLUMNS"] = str(
                term_columns + 1 if platform.system() == "Windows" else term_columns
            )
            command_env.pop("CI", None)

            command_env.update(env)

            result = sp.run(cmd, cwd=tmp_path, capture_output=True, env=command_env)

            print("run>", *cmd)
            print("stdout:")
            print(result.stdout.decode())
            print("stderr:")
            print(result.stderr.decode())

            if returncode is not None:
                assert result.returncode == returncode

            if report is not None:

                report_list = []
                record = False
                for line in result.stdout.decode().splitlines():
                    line = line.strip()
                    if line.startswith("===="):
                        record = False

                    if record and line:
                        report_list.append(line)

                    if line.startswith("====") and "inline snapshot" in line:
                        record = True

                report_str = "\n".join(report_list)

                report_str = ansi_escape.sub("", report_str)

                # fix windows problems
                report_str = report_str.replace("\u2500", "-")
                report_str = report_str.replace("\r", "")
                report_str = report_str.replace(" \n", " ⏎\n")

                assert report_str == report

            if changed_files is not None:
                current_files = {}

                for name, content in sorted(self.read_files(tmp_path).items()):
                    if name not in self.files or self.files[name] != content:
                        current_files[name] = content
                assert changed_files == current_files

            return Example(self.read_files(tmp_path))
