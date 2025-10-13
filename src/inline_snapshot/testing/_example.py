from __future__ import annotations

import os
import platform
import random
import re
import subprocess as sp
import sys
import tokenize
import traceback
import uuid
from argparse import ArgumentParser
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from typing import Callable
from unittest.mock import patch

from rich.console import Console

from inline_snapshot._exceptions import UsageError
from inline_snapshot._snapshot_session import SnapshotSession

from .._global_state import enter_snapshot_context
from .._global_state import leave_snapshot_context
from .._global_state import state
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

uuid.uuid4 = f
"""


@contextmanager
def chdir(path):
    cwd = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(cwd)


@contextmanager
def change_file(path: Path, map_function):
    exists = path.exists()
    if exists:
        text = path.read_bytes().decode("utf-8")
    else:
        text = ""

    path.write_bytes(map_function(text).encode("utf-8"))

    yield

    if exists:
        path.write_bytes(text.encode("utf-8"))
    else:
        path.unlink()


@contextmanager
def temp_environ(**kwargs):
    original = dict(os.environ)
    os.environ.update(kwargs)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(original)


class StopTesting(Exception):
    pass


class Example:
    files: dict[str, str | bytes]

    def __init__(self, files: str | bytes | dict[str, str | bytes]):
        """
        Parameters:
            files: a collection of files which are used as your example project,
                   or just a string which will be saved as *tests/test_something.py*.
        """
        if isinstance(files, (str, bytes)):
            files = {"tests/test_something.py": files}

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
                content = content.encode("utf-8")
            filename.write_bytes(content)

    def _read_files(self, dir: Path):

        def try_read(path: Path) -> str | bytes:
            code = path.read_bytes()
            try:
                return code.decode("utf-8")
            except UnicodeDecodeError:
                return code

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
        """
        Adds extra files to the example.

        Arguments:
            extra_files: dictionary of filenames and file contents.
        """
        return Example({**self.files, **extra_files})

    def read_file(self, filename: str) -> str:
        """
        Reads a file from the example.

        Arguments:
            filename: the filename.
        """
        text = self.files[filename]
        assert isinstance(text, str)
        return text

    read_text = read_file

    def change_code(self, mapping: Callable[[str], str]) -> Example:
        """
        Changes example tests by mapping every file with the given function.

        Arguments:
            mapping: function to apply to each file's content.
        """
        return Example(
            {
                name: mapping(text) if isinstance(text, str) else text
                for name, text in self.files.items()
            }
        )

    def replace(self, old_text: str, new_text: str) -> Example:
        """
        Changes example tests by replacing old_text with new_text.

        Arguments:
            old_text: the text to be replaced.
            new_text: the new text to use instead.
        """
        return self.change_code(lambda code: code.replace(old_text, new_text))

    def remove_file(self, filename: str) -> Example:
        """
        Removes a file from the example.

        Arguments:
            filename: the file to be removed.
        """
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
        stderr: Snapshot[str] | None = None,
    ) -> Example:
        """Execute the example files in process and run every `test_*`
        function.

        This is useful for fast test execution.

        Parameters:
            args: inline-snapshot arguments (supports only "--inline-snapshot=fix|create|...").
            reported_categories: snapshot of categories which inline-snapshot thinks could be applied.
            changed_files: snapshot of files which are changed by this run.
            raises: snapshot of the exception raised during test execution.
                    Required if your code raises an exception.

        Returns:
            A new Example instance containing the changed files.
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
        flags = {f for f in flags if f}

        with TemporaryDirectory() as dir:
            tmp_path = Path(dir)

            self._write_files(tmp_path)

            raised_exception = []

            with deterministic_uuid(), chdir(tmp_path), temp_environ(TERM="unknown"):
                session = SnapshotSession()

                def report_error(message):
                    raise StopTesting(message)

                snapshot_flags = set()
                try:
                    enter_snapshot_context()
                    session.load_config(
                        tmp_path / "pyproject.toml",
                        flags,
                        parallel_run=False,
                        error=report_error,
                        project_root=tmp_path,
                    )

                    report_output = StringIO()
                    console = Console(file=report_output, width=80)

                    tests_found = False
                    for filename in tmp_path.rglob("test_*.py"):
                        globals: dict[str, Any] = {}
                        print("run> pytest-inline", filename)
                        with tokenize.open(filename) as f:
                            code = f.read()
                        exec(
                            compile(code, filename, "exec"),
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

                                def fail(message):
                                    console.print(f"FAIL: {message}")

                                session.test_enter()
                                try:
                                    v()
                                finally:
                                    session.test_exit(fail=fail)
                            except Exception as e:
                                traceback.print_exc()
                                raised_exception.append(e)

                    if not tests_found:
                        raise UsageError("no test_*() functions in the example")

                    session.show_report(console)

                    for snapshot in state().snapshots.values():
                        for change in snapshot._changes():
                            snapshot_flags.add(change.flag)

                except StopTesting as e:
                    assert stderr == f"ERROR: {e}\n"
                finally:
                    leave_snapshot_context()

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
        """Run pytest with the given args and environment variables in a separate
        process.

        It can be used to test the interaction between your code and pytest, but it is a bit slower than `run_inline`.

        Parameters:
            args: pytest arguments like "--inline-snapshot=fix"
            env: dict of environment variables
            changed_files: snapshot of files changed by this run.
            report: snapshot of the report at the end of the pytest run.
            stderr: pytest stderr output
            returncode: snapshot of the pytest return code.

        Returns:
            A new Example instance containing the changed files.
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
            command_env.pop("PYTEST_XDIST_WORKER", None)

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

            result_stdout = result.stdout.decode("utf-8")
            result_stderr = result.stderr.decode("utf-8")

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
