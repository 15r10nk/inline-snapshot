import re
import shutil
from pathlib import Path

import black.files
import pytest

import inline_snapshot._inline_snapshot
from inline_snapshot import snapshot
from inline_snapshot._format import format_code


def test_help_message(testdir):
    result = testdir.runpytest_subprocess("--help")
    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["inline-snapshot:", "*--inline-snapshot*"])


class RunResult:
    def __init__(self, result):
        self._result = result

    def __getattr__(self, name):
        return getattr(self._result, name)

    @staticmethod
    def _join_lines(lines):
        text = "\n".join(lines).rstrip()

        if "\n" in text:
            return "\n" + text + "\n"
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

            if line.startswith("====") and "inline snapshot" in line:
                record = True
        return self._join_lines(result)

    def errorLines(self):
        return self._join_lines(
            [line for line in self.stdout.lines if line and line[:2] in ("> ", "E ")]
        )


@pytest.fixture
def project(pytester):
    class Project:
        def setup(self, source: str):
            self.header = "from inline_snapshot import snapshot\n"
            if not source.startswith(("import ", "from ")):
                self.header += "\n\n"

            source = self.header + source
            print("write code:")
            print(source)
            self._filename.write_text(source)

        @property
        def _filename(self):
            return pytester.path / "test_file.py"

        def is_formatted(self):
            code = self._filename.read_text()
            return code == format_code(code, self._filename)

        def format(self):
            self._filename.write_text(
                format_code(self._filename.read_text(), self._filename)
            )

        def pyproject(self, source):
            black.files.find_project_root.cache_clear()
            (pytester.path / "pyproject.toml").write_text(source)

        @property
        def source(self):
            return self._filename.read_text()[len(self.header) :]

        def run(self, *args):
            cache = pytester.path / "__pycache__"
            if cache.exists():
                shutil.rmtree(cache)

            result = pytester.runpytest_subprocess(*args)
            # print(help(pytester))

            return RunResult(result)

    return Project()


def test_create(project):
    project.setup(
        """
def test_a():
    assert 5==snapshot()
    """
    )

    result = project.run()

    result.assert_outcomes(errors=1, passed=1)

    assert result.report == snapshot(
        "Error: 1 snapshots are missing values (--inline-snapshot=create)"
    )

    result = project.run("--inline-snapshot=create")

    result.assert_outcomes(passed=1)

    assert result.report == snapshot("defined values for 1 snapshots")

    assert project.source == snapshot(
        """
def test_a():
    assert 5==snapshot(5)
    """
    )


def test_fix(project):
    project.setup(
        """
def test_a():
    assert 5==snapshot(4)
    """
    )

    result = project.run()

    result.assert_outcomes(failed=1)

    assert result.report == snapshot(
        "Error: 1 snapshots have incorrect values (--inline-snapshot=fix)"
    )

    result = project.run("--inline-snapshot=fix")

    result.assert_outcomes(passed=1)

    assert result.report == snapshot("fixed 1 snapshots")

    assert project.source == snapshot(
        """
def test_a():
    assert 5==snapshot(5)
    """
    )


def test_update(project):
    project.setup(
        """
def test_a():
    assert "5" == snapshot('''5''')
    """
    )

    result = project.run()

    result.assert_outcomes(passed=1)

    assert result.report == snapshot("")

    result = project.run("--inline-snapshot=update")

    assert result.report == snapshot("updated 1 snapshots")

    assert project.source == snapshot(
        """
def test_a():
    assert "5" == snapshot("5")
    """
    )


def test_trim(project):
    project.setup(
        """
def test_a():
    assert 5 in snapshot([4,5])
    """
    )

    result = project.run()

    result.assert_outcomes(passed=1)

    assert result.report == snapshot(
        "Info: 1 snapshots can be trimmed (--inline-snapshot=trim)"
    )

    result = project.run("--inline-snapshot=trim")

    assert result.report == snapshot("trimmed 1 snapshots")

    assert project.source == snapshot(
        """
def test_a():
    assert 5 in snapshot([5])
    """
    )


def test_multiple(project):
    project.setup(
        """
def test_a():
    assert "5" == snapshot('''5''')
    assert 5 <= snapshot(8)
    assert 5 == snapshot(4)
    """
    )

    result = project.run()

    result.assert_outcomes(failed=1)

    assert result.report == snapshot(
        """
Error: 1 snapshots have incorrect values (--inline-snapshot=fix)
Info: 1 snapshots can be trimmed (--inline-snapshot=trim)
"""
    )

    result = project.run("--inline-snapshot=trim,fix")

    assert result.report == snapshot(
        """
Info: 1 snapshots changed their representation (--inline-snapshot=update)
fixed 1 snapshots
trimmed 1 snapshots
updated 1 snapshots
"""
    )

    assert project.source == snapshot(
        """
def test_a():
    assert "5" == snapshot("5")
    assert 5 <= snapshot(5)
    assert 5 == snapshot(5)
    """
    )


def test_deprecated_option(project):
    project.setup(
        """
def test_a():
    pass
    """
    )

    result = project.run("--update-snapshots=failing")
    assert result.stderr.str().strip() == snapshot(
        "ERROR: --update-snapshots=failing is deprecated, please use --inline-snapshot=fix"
    )

    result = project.run("--update-snapshots=new")
    assert result.stderr.str().strip() == snapshot(
        "ERROR: --update-snapshots=new is deprecated, please use --inline-snapshot=create"
    )

    result = project.run("--update-snapshots=all")
    assert result.stderr.str().strip() == snapshot(
        "ERROR: --update-snapshots=all is deprecated, please use --inline-snapshot=create,fix"
    )

    result = project.run("--inline-snapshot-disable", "--inline-snapshot=fix")
    assert result.stderr.str().strip() == snapshot(
        "ERROR: --inline-snapshot-disable can not be combined with other flags (fix)"
    )

    result = project.run("--update-snapshots=failing", "--inline-snapshot=fix")
    assert result.stderr.str().strip() == snapshot(
        "ERROR: --update-snapshots=failing is deprecated, please use only --inline-snapshot"
    )


def test_black_config(project):
    project.setup(
        """
def test_a():
    assert list(range(10)) == snapshot([])
"""
    )

    project.format()

    assert project.is_formatted()

    project.pyproject(
        """
[tool.black]
line-length=50
    """
    )

    assert project.is_formatted()

    project.run("--inline-snapshot=fix")

    assert project.source == snapshot(
        """def test_a():
    assert list(range(10)) == snapshot(
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    )
"""
    )

    assert project.is_formatted()


def test_disabled(project):
    project.setup(
        """
def test_a():
    assert 4==snapshot(5)
    """
    )

    result = project.run("--inline-snapshot-disable")
    result.assert_outcomes(failed=1)

    result = project.run("--inline-snapshot=fix")
    assert project.source == snapshot(
        """
def test_a():
    assert 4==snapshot(4)
    """
    )

    result = project.run("--inline-snapshot-disable")
    result.assert_outcomes(passed=1)


def test_compare(project):
    project.setup(
        """
def test_a():
    assert "a"==snapshot("b")
    """
    )

    result = project.run()
    assert result.errorLines() == snapshot(
        """
>       assert "a"==snapshot("b")
E       AssertionError: assert 'a' == 'b'
E         - b
E         + a
"""
    )

    project.setup(
        """
def test_a():
    assert snapshot("b")=="a"
    """
    )

    result = project.run()
    assert result.errorLines() == snapshot(
        """
>       assert snapshot("b")=="a"
E       AssertionError: assert 'b' == 'a'
E         - a
E         + b
"""
    )


def test_assertion_error_loop(project):
    project.setup(
        """
for e in (1, 2):
    assert e == snapshot()
    """
    )
    result = project.run()
    assert result.errorLines() == snapshot(
        """
E   assert 2 == 1
E    +  where 1 = snapshot()
"""
    )


def test_assertion_error_multiple(project):
    project.setup(
        """
for e in (1, 2):
    assert e == snapshot(1)
    """
    )
    result = project.run()
    assert result.errorLines() == snapshot(
        """
E   assert 2 == 1
E    +  where 1 = snapshot(1)
"""
    )


def test_assertion_error(project):
    project.setup(
        """
assert 2 == snapshot(1)
    """
    )
    assert repr(snapshot) == "snapshot"
    result = project.run()
    assert result.errorLines() == snapshot(
        """
E   assert 2 == 1
E    +  where 1 = snapshot(1)
"""
    )


def test_run_without_pytest(pytester):
    # snapshots are deactivated by default
    pytester.makepyfile(
        test_file="""
from inline_snapshot import snapshot
s=snapshot([1,2])
assert isinstance(s,list)
assert s==[1,2]
    """
    )

    result = pytester.runpython("test_file.py")

    assert result.ret == 0


@pytest.mark.parametrize(
    "file",
    [
        pytest.param(file, id=file.stem)
        for file in [
            *(Path(__file__).parent.parent / "docs").rglob("*.md"),
            *(Path(__file__).parent.parent).glob("*.md"),
        ]
    ],
)
def test_docs(project, file, subtests):
    """
    test code blocks with the header
    <!-- inline-snapshot: options ... -->

    where options can be:
        * flags passed to --inline-snapshot=...
        * `this` to specify that the input source code should be the current block and not the last
        * `outcome-passed=2` to check for the pytest test outcome

    """
    block_start = re.compile("``` *python")
    block_end = re.compile("```.*")

    header = re.compile("<!-- inline-snapshot:(.*)-->")

    text = file.read_text()
    new_lines = []
    block_lines = []
    options = set()
    is_block = False
    code = None
    for linenumber, line in enumerate(text.splitlines(), start=1):
        if block_start.fullmatch(line.strip()) and is_block == True:
            block_lines = []
            new_lines.append(line)
            continue

        if block_end.fullmatch(line.strip()) and is_block:
            with subtests.test(line=linenumber):
                is_block = False

                last_code = code
                code = "\n".join(block_lines) + "\n"

                flags = options & {"fix", "update", "create", "trim"}

                args = ["--inline-snapshot", ",".join(flags)] if flags else []

                if flags and "this" not in options:
                    project.setup(last_code)
                else:
                    project.setup(code)

                result = project.run(*args)

                print("flags:", flags)

                new_code = code
                if flags:
                    new_code = project.source

                if (
                    inline_snapshot._inline_snapshot._update_flags.fix
                ):  # pragma: no cover
                    new_lines.append(new_code.rstrip("\n"))
                else:
                    new_lines += block_lines

                new_lines.append(line)

                if not inline_snapshot._inline_snapshot._update_flags.fix:
                    if flags:
                        assert result.ret == 0
                    else:
                        assert {
                            f"outcome-{k}={v}"
                            for k, v in result.parseoutcomes().items()
                        } == {flag for flag in options if flag.startswith("outcome-")}
                    assert code == new_code
                else:  # pragma: no cover
                    pass

            continue

        m = header.fullmatch(line.strip())
        if m:
            options = set(m.group(1).split())
            is_block = True
            new_lines.append(line)

        if is_block:
            block_lines.append(line)
        else:
            new_lines.append(line)

    if inline_snapshot._inline_snapshot._update_flags.fix:  # pragma: no cover
        file.write_text("\n".join(new_lines) + "\n")
