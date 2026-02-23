import os
import platform
import re
import shutil
import sys
import textwrap
from pathlib import Path
from unittest import mock

import black
import executing
from inline_snapshot._get_snapshot_value import get_snapshot_value
import pytest

from inline_snapshot._format import format_code
from inline_snapshot._snapshot_arg import snapshot_arg
from inline_snapshot.testing._example import Example
from tests.utils import Store

pytest_plugins = "pytester"


pytest.register_assert_rewrite("tests.example")

black.files.find_project_root = black.files.find_project_root.__wrapped__  # type: ignore


@pytest.fixture(autouse=True)
def check_pypy(request):
    implementation = sys.implementation.name
    node = request.node

    if implementation != "cpython" and node.get_closest_marker("no_rewriting") is None:
        pytest.skip(f"{implementation} is not supported")

    yield


def check_update(source_code, *, flags="", reported_flags=None, expected_code=...):
    code = f"""\
from inline_snapshot import snapshot,outsource

def test_a():
    exec(compile(open("source_code.py").read(),"source_code.py","exec"))
"""
    e = Example(
        {
            "pyproject.toml": """\
[tool.inline-snapshot]
show-updates=true""",
            "test_a.py": code,
            "source_code.py": textwrap.dedent(source_code),
        }
    )
    result = e.run_inline(
        [f"--inline-snapshot={flags}"],
        reported_categories=(result_flags := Store()),
    )

    flags_set = {*flags.split(",")} - {""}

    if get_snapshot_value(reported_flags):
        reported_flags_set = {*get_snapshot_value(reported_flags).split(",")} - {""}
    else:
        reported_flags_set = flags_set

    if reported_flags_set != set(result_flags.value):
        assert snapshot_arg(reported_flags) == ",".join(sorted(result_flags.value))

    assert (
        snapshot_arg(expected_code)
        == textwrap.dedent(
            result.read_file("source_code.py").split("# split")[-1]
        ).strip()
    )


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


class RunResult:
    def __init__(self, result):
        self._result = result

    def __getattr__(self, name):
        return getattr(self._result, name)

    @staticmethod
    def _join_lines(lines):
        text = "\n".join(lines).rstrip()

        if "\n" in text:
            return text + "\n"
        else:
            return text

    @property
    def report(self):
        result = []
        record = False
        for line in self._result.stdout.lines:
            line = line.strip()
            if line.startswith("===="):
                record = False

            if record and line:
                result.append(line)

            if line.startswith(("-----", "═════")) and "inline-snapshot" in line:
                record = True

        result = self._join_lines(result)

        result = ansi_escape.sub("", result)

        # fix windows problems
        result = result.replace("\u2500", "-")
        result = result.replace("\r", "")

        return result

    @property
    def errors(self):
        result = []
        record = False
        for line in self._result.stdout.lines:
            line = line.strip()

            if line.startswith("====") and "ERRORS" in line:
                record = True
            if record and line:
                result.append(line)
        result = self._join_lines(result)

        result = re.sub(r"\d+\.\d+s", "<time>", result)
        return result

    @property
    def stderr(self):
        original = self._result.stderr.lines
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
        return pytest.LineMatcher(lines)

    def errorLines(self):
        result = self._join_lines(
            [line for line in self.stdout.lines if line and line[:2] in ("> ", "E ")]
        )
        return result


@pytest.fixture
def project(pytester):  # pragma: no cover
    class Project:

        def __init__(self):
            self.term_columns = 80

        def setup(self, source: str, add_header=True):
            if add_header:
                self.header = """\
# äöß 🐍
from inline_snapshot import snapshot
from inline_snapshot import outsource
"""
                if "# no imports" in source:
                    self.header = """\
# äöß 🐍
"""
                else:
                    self.header = """\
# äöß 🐍
from inline_snapshot import snapshot
from inline_snapshot import outsource
"""
            else:  # pragma: no cover
                self.header = ""

            header = self.header
            if not source.startswith(("import ", "from ")):
                header += "\n\n"

            source = header + source
            print("write code:")
            print(source)
            self._filename.write_bytes(source.encode("utf-8"))

            (pytester.path / "conftest.py").write_bytes(
                b"""
import datetime
import pytest
from freezegun.api import FakeDatetime,FakeDate
from inline_snapshot.plugin import customize

class InlineSnapshotPlugin:
    @customize
    def fakedatetime_handler(self,value,builder):
        if isinstance(value,FakeDatetime):
            return builder.create_code(value.__repr__().replace("FakeDatetime","datetime.datetime"))

    @customize
    def fakedate_handler(self,value,builder):
        if isinstance(value,FakeDate):
            return builder.create_code(value.__repr__().replace("FakeDate","datetime.date"))


@pytest.fixture(autouse=True)
def set_time(freezer):
        freezer.move_to(datetime.datetime(2024, 3, 14, 0, 0, 0, 0))
        yield

import uuid
import random

rd = random.Random(0)

def f():
    return uuid.UUID(int=rd.getrandbits(128), version=4)

uuid.uuid4 = f

"""
            )

        @property
        def _filename(self):
            (pytester.path / "tests").mkdir(exist_ok=True)

            return pytester.path / "tests" / "test_file.py"

        def is_formatted(self):
            code = self._filename.read_text("utf-8")
            return code == format_code(code, self._filename)

        def format(self):
            self._filename.write_bytes(
                format_code(self._filename.read_text("utf-8"), self._filename).encode(
                    "utf-8"
                )
            )

        def pyproject(self, source):
            self.write_file("pyproject.toml", source)

        def write_file(self, filename, content):
            (pytester.path / filename).write_bytes(content.encode("utf-8"))

        def storage(self, storage_dir=".inline-snapshot"):
            if os.path.isabs(storage_dir):
                dir = Path(storage_dir)
            else:
                dir = pytester.path / storage_dir
            dir /= "external"

            if not dir.exists():
                return []

            return sorted(p.name for p in dir.iterdir() if p.name != ".gitignore")

        @property
        def source(self):
            assert self._filename.read_text("utf-8")[: len(self.header)] == self.header
            return self._filename.read_text("utf-8")[len(self.header) :].lstrip()

        def run(self, *args, stdin=""):
            cache = pytester.path / "__pycache__"
            if cache.exists():
                shutil.rmtree(cache)

            # pytest adds -v if it detects some github CI variable
            old_environ = dict(os.environ)
            if "CI" in os.environ:
                del os.environ["CI"]  # pragma: no cover

            os.environ.pop("GITHUB_ACTIONS", None)
            os.environ.pop("PYTEST_XDIST_WORKER", None)

            try:
                with mock.patch.dict(
                    os.environ,
                    {
                        "TERM": "unknown",
                        "COLUMNS": str(
                            self.term_columns + 1
                            if platform.system() == "Windows"
                            else self.term_columns
                        ),
                    },
                ):

                    if stdin:
                        result = pytester.run("pytest", *args, stdin=stdin)
                    else:
                        result = pytester.run("pytest", *args)
            finally:
                os.environ.update(old_environ)

            return RunResult(result)

    return Project()


@pytest.fixture(params=[True, False], ids=["executing", "without-executing"])
def executing_used(request, monkeypatch):
    used = request.param
    if used:
        yield used
    else:
        real_executing = executing.Source.executing

        def fake_executing(frame):
            result = real_executing(frame)
            result.node = None
            return result

        monkeypatch.setattr(executing.Source, "executing", fake_executing)
        yield used
