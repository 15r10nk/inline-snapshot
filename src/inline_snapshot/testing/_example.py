from __future__ import annotations

import os
import platform
import random
import re
import subprocess as sp
import sys
import traceback
import uuid
from argparse import ArgumentParser
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

from rich.console import Console

from inline_snapshot._config import Config
from inline_snapshot._config import read_config
from inline_snapshot._exceptions import UsageError
from inline_snapshot._external._storage._hash import HashStorage
from inline_snapshot._problems import report_problems

from .._change import ChangeBase
from .._change import apply_all
from .._flags import Flags
from .._global_state import snapshot_env
from .._rewrite_code import ChangeRecorder
from .._types import Category
from .._types import Snapshot

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


def normalize(text):
    text = ansi_escape.sub("", text)

    # fix windows problems
    text = text.replace("\u2500", "-")
    text = text.replace("\r", "")
    return text


@contextmanager
def deterministic_uuid():
    rd = random.Random(0)

    def f():
        return uuid.UUID(int=rd.getrandbits(128), version=4)

    with patch("uuid.uuid4", new=f):
        yield


# this code is copied from pytest

# Regex to match the session duration string in the summary: "74.34s".
rex_session_duration = re.compile(r"\d+\.\d\ds")
# Regex to match all the counts and phrases in the summary line: "34 passed, 111 skipped".
rex_outcome = re.compile(r"(\d+) (\w+)")


def parse_outcomes(lines):
    for line in reversed(lines):
        if rex_session_duration.search(line):
            outcomes = rex_outcome.findall(line)
            ret = {noun: int(count) for (count, noun) in outcomes}
            break
        else:
            pass  # pragma: no cover
    else:
        raise ValueError("Pytest terminal summary report not found")  # pragma: no cover

    to_plural = {
        "warning": "warnings",
        "error": "errors",
    }
    return {to_plural.get(k, k): v for k, v in ret.items()}


conftest_footer = """
import uuid
import random

rd = random.Random(0)

def f():
    return uuid.UUID(int=rd.getrandbits(128), version=4)

uuid.uuid4=f
"""


@contextmanager
def change_file(path, map_function):
    exists = path.exists()
    if exists:
        text = path.read_text()
    else:
        text = ""

    path.write_text(map_function(text))

    yield

    if exists:
        path.write_text(text)
    else:
        path.unlink()


class Example:
    files: dict[str, str | bytes]

    def __init__(self, files: str | dict[str, str | bytes]):
        """
        Parameters:
            files: a collection of files where inline-snapshot operates on,
                   or just a string which will be saved as *test_something.py*.
        """
        if isinstance(files, str):
            files = {"test_something.py": files}

        self.files = files

    def dump_files(self):
        from rich.panel import Panel
        from rich.text import Text

        console = Console()

        for name, content in self.files.items():
            if isinstance(content, bytes):
                content = repr(content)
            console.print(Panel(Text(content), title=name))

    def _write_files(self, dir: Path):
        for name, content in self.files.items():
            filename = dir / name
            filename.parent.mkdir(exist_ok=True, parents=True)
            if isinstance(content, str):
                filename.write_text(content)
            else:
                filename.write_bytes(content)

    def _read_files(self, dir: Path):

        def try_read(path: Path):
            try:
                return path.read_text("utf-8")
            except UnicodeDecodeError:
                return path.read_bytes()

        def normalize_path(path):
            return str(path.relative_to(dir)).replace("\\", "/")

        return {
            normalize_path(p): try_read(p)
            for p in dir.rglob("*")
            if p.is_file()
            and p.name != ".gitignore"
            and p.suffix != ".pyc"
            and ".pytest_cache" not in p.parts
        }

    def with_files(self, extra_files: dict[str, str | bytes]) -> Example:
        return Example({**self.files, **extra_files})

    def read_text(self, name: str) -> str:
        text = self.files[name]
        assert isinstance(text, str)
        return text

    def change_code(self, func) -> Example:
        return Example({name: func(text) for name, text in self.files.items()})

    def replace(self, text, new_text) -> Example:
        return self.change_code(lambda code: code.replace(text, new_text))

    def remove_file(self, filename):
        return Example(
            {name: file for name, file in self.files.items() if name != filename}
        )

    def run_inline(
        self,
        args: list[str] = [],
        *,
        reported_categories: Snapshot[list[Category]] | None = None,
        changed_files: Snapshot[dict[str, str]] | None = None,
        report: Snapshot[str] | None = None,
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
        self.dump_files()

        with TemporaryDirectory() as dir:
            tmp_path = Path(dir)

            self._write_files(tmp_path)

            raised_exception = []

            with snapshot_env() as state, deterministic_uuid():

                recorder = ChangeRecorder()
                state.update_flags = Flags({*flags})
                state.all_storages["hash"] = HashStorage(
                    tmp_path / ".inline-snapshot" / "external"
                )
                state.config = Config()
                read_config(tmp_path / "pyproject.toml", state.config)
                if state.config.storage_dir is None:
                    state.config.storage_dir = tmp_path / ".inline_snapshot"
                else:
                    pass  # pragma: no cover

                try:
                    tests_found = False
                    for filename in tmp_path.glob("*.py"):
                        globals: dict[str, Any] = {}
                        print("run> pytest-inline", filename)
                        exec(
                            compile(filename.read_text("utf-8"), filename, "exec"),
                            globals,
                        )

                        # run all test_* functions
                        tests = [
                            v
                            for k, v in globals.items()
                            if (k.startswith("test_") or k == "test") and callable(v)
                        ]
                        tests_found |= len(tests) != 0

                        for v in tests:
                            try:
                                v()
                            except Exception as e:
                                traceback.print_exc()
                                raised_exception.append(e)

                    if not tests_found:
                        raise UsageError("no test_*() functions in the example")
                finally:
                    state.active = False

                changes: list[ChangeBase] = []
                for snapshot in state.snapshots.values():
                    changes += list(snapshot._changes())

                snapshot_flags = {change.flag for change in changes}

                apply_all(
                    [
                        change
                        for change in changes
                        if change.flag in state.update_flags.to_set()
                    ],
                    recorder,
                )
                recorder.fix_all()

                for change in changes:
                    if change.flag in state.update_flags.to_set():
                        change.apply_external_changes()

                report_output = StringIO()
                console = Console(file=report_output, width=80)

                # TODO: add all the report output here
                report_problems(lambda: console)

            if reported_categories is not None:
                assert sorted(snapshot_flags) == reported_categories

            if raised_exception:
                if raises is None:
                    raise raised_exception[0]

                assert raises == "\n".join(
                    f"{type(e).__name__}:\n" + str(e) for e in raised_exception
                )
            else:
                assert raises == None

            if changed_files is not None:
                assert changed_files == self._changed_files(tmp_path)

            if report is not None:
                assert report == normalize(report_output.getvalue())

            return Example(self._read_files(tmp_path))

    def _changed_files(self, tmp_path):
        current_files = {}
        all_current_files = self._read_files(tmp_path)

        for name, content in sorted(all_current_files.items()):
            if name not in self.files or self.files[name] != content:
                current_files[name] = content

        for name in self.files:
            if name not in all_current_files:
                current_files[name] = None

        return current_files

    def run_pytest(
        self,
        args: list[str] = [],
        *,
        term_columns=80,
        env: dict[str, str] = {},
        changed_files: Snapshot[dict[str, str]] | None = None,
        report: Snapshot[str] | None = None,
        error: Snapshot[str] | None = None,
        stderr: Snapshot[str] | None = None,
        returncode: Snapshot[int] = 0,
        stdin: bytes = b"",
        outcomes: Snapshot[dict[str, int]] | None = None,
    ) -> Example:
        """Run pytest with the given args and env variables in an separate
        process.

        It can be used to test the interaction between your code and pytest, but it is a bit slower than `run_inline`

        Parameters:
            args: pytest arguments like "--inline-snapshot=fix"
            env: dict of environment variables
            changed_files: snapshot of files which are changed by this run.
            report: snapshot of the report at the end of the pytest run.
            stderr: pytest stderr output
            returncode: snapshot of the pytest returncode.

        Returns:
            A new Example instance which contains the changed files.
        """
        self.dump_files()

        with TemporaryDirectory() as dir:
            tmp_path = Path(dir)

            self._write_files(tmp_path)

            cmd = [sys.executable, "-m", "pytest", *args]

            command_env = dict(os.environ)
            command_env["TERM"] = "unknown"
            command_env["COLUMNS"] = str(
                term_columns + 1 if platform.system() == "Windows" else term_columns
            )
            command_env.pop("CI", None)
            command_env.pop("GITHUB_ACTIONS", None)

            if stdin:
                # makes Console.is_terminal == True
                command_env["FORCE_COLOR"] = "true"

            command_env.update(env)

            with change_file(
                tmp_path / "conftest.py", lambda text: text + conftest_footer
            ):
                result = sp.run(
                    cmd, cwd=tmp_path, capture_output=True, env=command_env, input=stdin
                )

            result_stdout = result.stdout.decode()
            result_stderr = result.stderr.decode()
            result_returncode = result.returncode

            print("run>", *cmd)
            print("stdout:")
            print(result_stdout)
            print("stderr:")
            print(result_stderr)

            assert result.returncode == returncode

            if stderr is not None:

                original = result_stderr.splitlines()
                lines = [
                    line
                    for line in original
                    if not any(
                        s in line
                        for s in [
                            'No entry for terminal type "unknown"',
                            "using dumb terminal settings.",
                        ]
                    )
                ]

                assert "\n".join(lines) == stderr

            if report is not None:

                report_list = []
                record = False
                for line in result_stdout.splitlines():
                    line = normalize(line.strip())
                    if line.startswith("===="):
                        record = False

                    if record and line:
                        report_list.append(line)

                    if (
                        line.startswith(("-----", "═════"))
                        and "inline-snapshot" in line
                    ):
                        record = True

                report_str = "\n".join(report_list)

                assert report_str == report, repr(report_str)

            if error is not None:
                assert (
                    error
                    == "\n".join(
                        [
                            line
                            for line in result_stdout.splitlines()
                            if line and line[:2] in ("> ", "E ")
                        ]
                    )
                    + "\n"
                )

            if changed_files is not None:
                assert changed_files == self._changed_files(tmp_path)

            if outcomes is not None:
                assert outcomes == parse_outcomes(result_stdout.splitlines())

            return Example(self._read_files(tmp_path))
