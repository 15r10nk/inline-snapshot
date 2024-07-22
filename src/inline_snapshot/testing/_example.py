from __future__ import annotations

import contextlib
import os
import platform
import re
import subprocess as sp
from argparse import ArgumentParser
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import inline_snapshot._external
import inline_snapshot._external as external
from inline_snapshot import _inline_snapshot
from inline_snapshot._inline_snapshot import Flags
from inline_snapshot._rewrite_code import ChangeRecorder
from inline_snapshot._types import Category
from inline_snapshot._types import Snapshot


@contextlib.contextmanager
def snapshot_env():
    import inline_snapshot._inline_snapshot as inline_snapshot

    current = (
        inline_snapshot.snapshots,
        inline_snapshot._update_flags,
        inline_snapshot._active,
        external.storage,
        inline_snapshot._files_with_snapshots,
        inline_snapshot._missing_values,
    )

    inline_snapshot.snapshots = {}
    inline_snapshot._update_flags = inline_snapshot.Flags()
    inline_snapshot._active = True
    external.storage = None
    inline_snapshot._files_with_snapshots = set()
    inline_snapshot._missing_values = 0

    try:
        yield
    finally:
        (
            inline_snapshot.snapshots,
            inline_snapshot._update_flags,
            inline_snapshot._active,
            external.storage,
            inline_snapshot._files_with_snapshots,
            inline_snapshot._missing_values,
        ) = current


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
    def __init__(self, files: str | dict[str, str]):
        """
        Parameters:
            files: a collecton of files where inline-snapshot opperates on,
                   or just a string which will be saved as *test_something.py*.
        """
        if isinstance(files, str):
            files = {"test_something.py": files}

        self.files = files

    def _write_files(self, dir: Path):
        for name, content in self.files.items():
            (dir / name).write_text(content)

    def _read_files(self, dir: Path):
        return {p.name: p.read_text() for p in dir.iterdir() if p.is_file()}

    def run_inline(
        self,
        args: list[str] = [],
        *,
        reported_categories: Snapshot[list[Category]] | None = None,
        changed_files: Snapshot[dict[str, str]] | None = None,
        raises: Snapshot[str] | None = None,
    ) -> Example:
        """Execute the example files in process and run every `test_*`
        function.

        This is useful for fast test execution.

        Parameters:
            args: inline-snapshot arguments (supports only "--inline-snapshot=fix|create|..." ).
            reported_categories: snapshot of categories which inline-snapshot thinks could be applied.
            changed_files: snapshot of files which are changed by this run.
            raises: snapshot of the exception which is raised during the test execution.
                    It is required if your code raises an exception.

        Returns:
            A new Example instance which contains the changed files.
        """

        parser = ArgumentParser()

        parser.add_argument(
            "--inline-snapshot",
            metavar="(disable,short-report,report,review,create,update,trim,fix)*",
            dest="inline_snapshot",
            help="update specific snapshot values:\n"
            "disable: disable the snapshot logic\n"
            "short-report: show a short report\n"
            "report: show a longer report with a diff report\n"
            "review: allow to approve the changes interactive\n"
            "create: creates snapshots which are currently not defined\n"
            "update: update snapshots even if they are defined\n"
            "trim: changes the snapshot in a way which will make the snapshot more precise.\n"
            "fix: change snapshots which currently break your tests\n",
        )
        parsed_args = parser.parse_args(args)
        flags = (parsed_args.inline_snapshot or "").split(",")

        with TemporaryDirectory() as dir:
            tmp_path = Path(dir)

            self._write_files(tmp_path)

            with snapshot_env():
                with ChangeRecorder().activate() as recorder:
                    _inline_snapshot._update_flags = Flags({*flags})
                    inline_snapshot._external.storage = (
                        inline_snapshot._external.DiscStorage(tmp_path / ".storage")
                    )

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
                    except Exception as e:
                        assert raises == f"{type(e).__name__}:\n" + str(e)

                    finally:
                        _inline_snapshot._active = False

                    snapshot_flags = set()

                    for snapshot in _inline_snapshot.snapshots.values():
                        snapshot_flags |= snapshot._flags
                        snapshot._change()

            if reported_categories is not None:
                assert sorted(snapshot_flags) == reported_categories

            recorder.fix_all()

            if changed_files is not None:
                current_files = {}

                for name, content in sorted(self._read_files(tmp_path).items()):
                    if name not in self.files or self.files[name] != content:
                        current_files[name] = content
                assert changed_files == current_files

            return Example(self._read_files(tmp_path))

    def run_pytest(
        self,
        args: list[str] = [],
        *,
        env: dict[str, str] = {},
        changed_files: Snapshot[dict[str, str]] | None = None,
        report: Snapshot[str] | None = None,
        returncode: Snapshot[int] | None = None,
    ) -> Example:
        """Run pytest with the given args and env variables in an seperate
        process.

        It can be used to test the interaction between your code and pytest, but it is a bit slower than `run_inline`

        Parameters:
            args: pytest arguments like "--inline-snapshot=fix"
            env: dict of environment variables
            changed_files: snapshot of files which are changed by this run.
            report: snapshot of the report at the end of the pytest run.
            returncode: snapshot of the pytest returncode.

        Returns:
            A new Example instance which contains the changed files.
        """

        with TemporaryDirectory() as dir:
            tmp_path = Path(dir)
            self._write_files(tmp_path)

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

                for name, content in sorted(self._read_files(tmp_path).items()):
                    if name not in self.files or self.files[name] != content:
                        current_files[name] = content
                assert changed_files == current_files

            return Example(self._read_files(tmp_path))
