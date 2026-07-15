import itertools
import platform
import re
import shlex
import sys
import textwrap
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Generic
from typing import List
from typing import Optional
from typing import TypeVar

import isort.api
import pytest
from dirty_equals import AnyThing
from dirty_equals import IsStr
from executing import is_pytest_compatible
from rich.markup import escape

from inline_snapshot import snapshot
from inline_snapshot._align import align
from inline_snapshot._external._external_file import external_file
from inline_snapshot._flags import Flags
from inline_snapshot._global_state import snapshot_env
from inline_snapshot._snapshot_arg import snapshot_arg
from inline_snapshot._unmanaged import declare_unmanaged
from inline_snapshot.extra import raises
from inline_snapshot.testing import Example
from inline_snapshot.testing._terminal_svg import render_ansi_to_svg
from inline_snapshot.version import is_insider


def normalize_terminal_output(output: str) -> str:
    return re.sub(r"in \d+\.\d+s", "in 0.00s", output)


@dataclass
class Block:
    code: str
    code_header: Optional[str]
    block_options: Dict[str, str]
    line: int


def map_code_blocks(file: Path, func, map_last_output=None, run=None):

    block_start = re.compile("( *)``` *python(.*)")
    block_end = re.compile("```.*")
    image = re.compile(r"( *)!\[[^\]]*\]\(([^)]+\.svg)\)")
    last_output_marker = "inline-snapshot-last-output"

    header = re.compile("<!--(.*)-->")

    current_code = file.read_text("utf-8")
    new_lines = []
    block_lines: List[str] = []
    is_block = False
    code = None
    indent = ""
    block_start_linenum: Optional[int] = None
    block_options: dict[str, str] = {}
    code_header = None
    header_line = ""
    block_found = False

    def is_last_output_marker(header: Optional[str]) -> bool:
        return header == last_output_marker or (
            header is not None and header.startswith(f"{last_output_marker}:")
        )

    def last_output_prompt(header: str) -> Optional[str]:
        if header == last_output_marker:
            return None
        return header.removeprefix(f"{last_output_marker}:").strip()

    def handle_inline_snapshot_run(line_number: int) -> None:
        nonlocal code_header
        nonlocal header_line
        if not code_header or not code_header.startswith("inline-snapshot-run:"):
            return
        if run is None:
            raise AssertionError(
                f"{file}:{line_number}: inline-snapshot-run has no runner"
            )
        new_code_header = run(code_header, line_number + 1)
        if new_code_header is not None:
            indent = header_line.split("<!--", 1)[0]
            header_line = f"{indent}<!-- {new_code_header.strip()} -->"
        code_header = None

    for linenumber, line in enumerate(current_code.splitlines(), start=1):
        m = block_start.fullmatch(line)
        if m and not is_block and is_last_output_marker(code_header):
            raise AssertionError(
                f"{file}:{linenumber - 1}: inline-snapshot-last-output must be followed by an SVG image"
            )

        if (
            m
            and not is_block
            and code_header
            and code_header.startswith("inline-snapshot-run:")
        ):
            raise AssertionError(
                f"{file}:{linenumber - 1}: inline-snapshot-run does not use a code block"
            )

        if m and not is_block:
            # ``` python
            block_found = True
            block_start_linenum = linenumber
            indent = m[1]
            block_options = {m[0]: m[1] for m in re.findall(r'(\w*)="([^"]*)"', m[2])}
            block_lines = []
            is_block = True
            continue

        if block_end.fullmatch(line.strip()) and is_block:
            # ```
            is_block = False
            assert block_start_linenum is not None

            code = "\n".join(block_lines) + "\n"
            code = textwrap.dedent(code)
            if file.suffix == ".py":
                code = code.replace("\\\\", "\\")

            try:
                new_block = func(
                    Block(
                        code=code,
                        code_header=code_header,
                        block_options=block_options,
                        line=block_start_linenum,
                    )
                )
            except Exception:
                print(f"error at block at line {block_start_linenum}")
                print(f"{code_header=}")
                print(f"{block_options=}")
                print(code)
                raise

            if new_block.code_header is not None:
                new_lines.append(f"{indent}<!-- {new_block.code_header.strip()} -->")

            options = " ".join(f'{k}="{v}"' for k, v in new_block.block_options.items())

            new_lines.append(f"{indent}``` {('python '+options).strip()}")

            new_code = new_block.code.rstrip()
            if file.suffix == ".py":
                new_code = new_code.replace("\\", "\\\\")
            new_code = textwrap.indent(new_code, indent)

            new_lines.append(new_code)

            new_lines.append(f"{indent}```")

            header_line = ""
            code_header = None

            continue

        if is_block:
            block_lines.append(line)
            continue

        m = header.fullmatch(line.strip())
        if m:
            # comment <!-- ... -->
            if header_line:
                if is_last_output_marker(code_header):
                    raise AssertionError(
                        f"{file}:{linenumber - 1}: inline-snapshot-last-output must be followed by an SVG image"
                    )
                handle_inline_snapshot_run(linenumber - 1)
                new_lines.append(header_line)
                code_header = None
                header_line = ""

            header_line = line
            code_header = m[1].strip()
            continue
        else:
            if header_line:
                if is_last_output_marker(code_header):
                    assert code_header is not None
                    image_match = image.fullmatch(line)
                    if image_match is None:
                        raise AssertionError(
                            f"{file}:{linenumber - 1}: inline-snapshot-last-output must be followed by an SVG image"
                        )
                    if map_last_output is None:
                        raise AssertionError(
                            f"{file}:{linenumber - 1}: inline-snapshot-last-output has no output handler"
                        )

                    map_last_output(
                        file.parent / image_match[2],
                        linenumber,
                        last_output_prompt(code_header),
                    )

                elif code_header and code_header.startswith("inline-snapshot-run:"):
                    handle_inline_snapshot_run(linenumber - 1)

                new_lines.append(header_line)
                code_header = None
                header_line = ""

        new_lines.append(line)

    if header_line:
        handle_inline_snapshot_run(linenumber)
        new_lines.append(header_line)

    new_code = "\n".join(new_lines) + "\n"

    if block_found or new_code != current_code and new_code.strip():
        assert external_file(file, format=".txt") == new_code


def test_map_code_blocks(tmp_path):

    file = tmp_path / "example.md"

    def test_doc(
        markdown_code,
        handle_block=lambda block: exec(block.code),
        handle_last_output=None,
        handle_run=None,
        blocks=[],
        last_output_calls=[],
        run_calls=[],
        exception="<no exception>",
        new_markdown_code=None,
    ):

        file.write_bytes(markdown_code.encode("utf-8"))

        recorded_blocks = []

        with raises(snapshot_arg(exception)):

            def test_block(block):
                handle_block(block)
                recorded_blocks.append(block)
                return block

            recorded_last_output_calls = []

            def test_last_output(path, line, prompt):
                assert handle_last_output is not None
                handle_last_output(path, line, prompt)
                recorded_last_output_calls.append(
                    (path.relative_to(file.parent), line, prompt)
                )

            recorded_run_calls = []

            def test_run(header, line):
                assert handle_run is not None
                new_header = handle_run(header, line)
                recorded_run_calls.append((header, line))
                return new_header

            with snapshot_env() as state:
                state.update_flags.fix = True
                state.active = True

                map_code_blocks(
                    file,
                    test_block,
                    test_last_output if handle_last_output is not None else None,
                    test_run if handle_run is not None else None,
                )

                for snapshot in state.snapshots.values():
                    for change in snapshot._changes():
                        change.apply_external_changes()

            assert recorded_blocks == blocks
            assert recorded_last_output_calls == last_output_calls
            assert recorded_run_calls == run_calls

            with snapshot_env():
                map_code_blocks(
                    file,
                    test_block,
                    test_last_output if handle_last_output is not None else None,
                    test_run if handle_run is not None else None,
                )

        recorded_markdown_code = file.read_text()
        if recorded_markdown_code != markdown_code:
            assert new_markdown_code == recorded_markdown_code
        else:
            assert new_markdown_code is None

    test_doc(
        """
``` python
1 / 0
```
""",
        exception=snapshot("ZeroDivisionError: division by zero"),
    )

    test_doc(
        """\
text
``` python
print(1 + 1)
```
text
<!-- inline-snapshot: create test -->
``` python hl_lines="1 2 3"
print(1 - 1)
```
text
""",
        blocks=snapshot(
            [
                Block(
                    code="print(1 + 1)\n", code_header=None, block_options={}, line=2
                ),
                Block(
                    code="print(1 - 1)\n",
                    code_header="inline-snapshot: create test",
                    block_options={"hl_lines": "1 2 3"},
                    line=7,
                ),
            ]
        ),
    )

    def change_block(block):
        block.code = "# removed"
        block.code_header = "header"
        block.block_options = {"a": "b c"}

    test_doc(
        """\
text
``` python
print(1 + 1)
```
""",
        handle_block=change_block,
        blocks=snapshot(
            [
                Block(
                    code="# removed",
                    code_header="header",
                    block_options={"a": "b c"},
                    line=2,
                )
            ]
        ),
        new_markdown_code=snapshot("""\
text
<!-- header -->
``` python a="b c"
# removed
```
"""),
    )

    test_doc(
        """\
text
``` python
print(1 + 1)
```
<!-- inline-snapshot-last-output -->
![](output.svg)
""",
        handle_last_output=lambda path, line, prompt: None,
        blocks=snapshot(
            [Block(code="print(1 + 1)\n", code_header=None, block_options={}, line=2)]
        ),
        last_output_calls=snapshot([(Path("output.svg"), 6, None)]),
    )

    test_doc(
        """\
text
``` python
print(1 + 1)
```
<!-- inline-snapshot-last-output: pytest -->
![](output.svg)
""",
        handle_last_output=lambda path, line, prompt: None,
        blocks=snapshot(
            [Block(code="print(1 + 1)\n", code_header=None, block_options={}, line=2)]
        ),
        last_output_calls=snapshot([(Path("output.svg"), 6, "pytest")]),
    )

    test_doc(
        """\
<!-- inline-snapshot-last-output -->
<!-- inline-snapshot: create -->
``` python
print(1)
```
""",
        exception=IsStr(
            regex=r"AssertionError: .*example\.md:1: inline-snapshot-last-output must be followed by an SVG image"
        ),
    )

    test_doc(
        """\
<!-- inline-snapshot-last-output -->
``` python
print(1)
```
""",
        exception=IsStr(
            regex=r"AssertionError: .*example\.md:1: inline-snapshot-last-output must be followed by an SVG image"
        ),
    )

    test_doc(
        """\
<!-- inline-snapshot-last-output -->
![](output.svg)
""",
        exception=IsStr(
            regex=r"AssertionError: .*example\.md:1: inline-snapshot-last-output has no output handler"
        ),
    )

    test_doc(
        """\
<!-- inline-snapshot-last-output -->
not an image
""",
        exception=IsStr(
            regex=r"AssertionError: .*example\.md:1: inline-snapshot-last-output must be followed by an SVG image"
        ),
    )

    test_doc(
        """\
text
<!-- inline-snapshot-run: report -->
more text
""",
        handle_run=lambda header, line: None,
        run_calls=snapshot([("inline-snapshot-run: report", 3)]),
    )

    test_doc(
        """\
text
<!-- inline-snapshot-run: report -->
more text
""",
        exception=IsStr(
            regex=r"AssertionError: .*example\.md:2: inline-snapshot-run has no runner"
        ),
    )

    test_doc(
        """\
text
<!-- inline-snapshot-run: report -->
more text
""",
        handle_run=lambda header, line: "inline-snapshot-run: report outcome-passed=1",
        run_calls=snapshot([("inline-snapshot-run: report", 3)]),
        new_markdown_code=snapshot("""\
text
<!-- inline-snapshot-run: report outcome-passed=1 -->
more text
"""),
    )

    test_doc(
        """\
<!-- inline-snapshot-run: report -->
""",
        handle_run=lambda header, line: None,
        run_calls=snapshot([("inline-snapshot-run: report", 2)]),
    )

    test_doc(
        """\
text
<!-- inline-snapshot: create -->
<!-- inline-snapshot-last-output -->
![](output.svg)
""",
        exception=IsStr(
            regex=r"AssertionError: .*example\.md:3: inline-snapshot-last-output has no output handler"
        ),
    )

    test_doc(
        """\
<!-- inline-snapshot-run: report -->
``` python
print(1)
```
""",
        exception=IsStr(
            regex=r"AssertionError: .*example\.md:1: inline-snapshot-run does not use a code block"
        ),
    )


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="\\r in stdout can cause problems in snapshot strings",
)
@pytest.mark.skipif(
    sys.version_info[:2] != (3, 12),
    reason="there is no reason to test the doc with different python versions",
)
@pytest.mark.parametrize(
    "file",
    [
        pytest.param(file, id=file.name)
        for file in [
            *(Path(__file__).parent.parent / "docs").rglob("*.md"),
            *(Path(__file__).parent.parent).glob("*.md"),
            *(Path(__file__).parent.parent / "src").rglob("*.py"),
        ]
    ],
)
def test_docs(file):
    file_test(file)


T = TypeVar("T")


@declare_unmanaged
class Store(Generic[T]):
    value: T

    def __eq__(self, other: Any):
        self.value = other
        return True


def file_test(
    file: Path,
    width: int = 80,
):
    """Test code blocks with the header <!-- inline-snapshot: options ... -->

    where options can be:
        * flags passed to --inline-snapshot=...
        * `first_block` to specify that the input source code should be the current block and not the last
        * `outcome-passed=2` to check for the pytest test outcome
    """

    last_code = None
    terminal_width = 80

    std_files = {
        "pyproject.toml": f"""
[tool.inline-snapshot]
format-command="black --stdin-filename {{filename}} -"

[tool.black]
line-length={width}
""",
        "conftest.py": """
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

uuid.uuid4=f


""",
    }

    extra_files: Dict[str, List[str]] = defaultdict(list)
    last_pytest_command: Optional[str] = None
    last_pytest_stdout: Optional[str] = None

    def map_last_output(
        image_path: Path, line: int, prompt: Optional[str] = None
    ) -> None:
        if last_pytest_command is None or last_pytest_stdout is None:
            raise AssertionError(
                f"{file}:{line - 1}: inline-snapshot-last-output needs a previous inline-snapshot block"
            )  # pragma: no cover

        command = last_pytest_command if prompt is None else prompt
        rendered = render_ansi_to_svg(
            normalize_terminal_output(last_pytest_stdout),
            width=terminal_width,
            title="Terminal",
            prompt=(
                f"[bold blue]$[/bold blue] "
                f"[bold white]{escape(command)}[/bold white]"
            ),
        )

        assert external_file(image_path.resolve(), format=".rich.svg") == rendered

    def run_example(code: str, code_header: str, block: Optional[Block] = None):
        nonlocal last_pytest_command
        nonlocal last_pytest_stdout

        raw_options = shlex.split(code_header)
        options = set(raw_options)
        stdin = b""
        stdin_text = ""
        stdin_options = []
        for option in raw_options:
            if option.startswith("stdin="):
                stdin_text = (
                    option.removeprefix("stdin=")
                    .encode("utf-8")
                    .decode("unicode_escape")
                )
                stdin_options.append(
                    f'stdin="{stdin_text.encode("unicode_escape").decode("ascii")}"'
                )
                stdin = stdin_text.encode("utf-8")

        if "requires_assert" in options and (
            not is_pytest_compatible() or not is_insider
        ):
            return None

        flags = options & Flags.all().to_set()
        cli_flags = flags | (options & {"disable", "report", "review", "short-report"})

        args = ["--inline-snapshot", ",".join(sorted(cli_flags))] if cli_flags else []
        pytest_args = [*args, "--no-header"]
        display_command = "pytest " + "=".join(args)

        outcomes = Store[Dict[str, int]]()
        returncode = Store[int]()
        stdout = Store[str]()

        if flags and "first_block" not in options:
            assert last_code is not None
            test_files = {"tests/test_example.py": last_code}
        else:
            code = isort.api.sort_code_string(
                code,
                config=isort.Config(
                    profile="black",
                    combine_as_imports=True,
                    lines_between_sections=0,
                ),
            )
            if block is not None:
                block.code = code
            test_files = {"tests/test_example.py": code}

        example = Example({**std_files, **test_files})
        if extra_files:
            all_files = [
                [(key, file) for file in files] for key, files in extra_files.items()
            ]
            for files in itertools.product(*all_files):
                example = example.with_files(dict(files))

                print("run with")
                example = example.run_pytest(
                    pytest_args,
                    outcomes=outcomes,
                    returncode=returncode,
                    changed_files=AnyThing(),
                    error=AnyThing(),
                    stdin=stdin,
                    stdout=stdout,
                    term_columns=terminal_width,
                )

        else:
            example = example.run_pytest(
                pytest_args,
                outcomes=outcomes,
                returncode=returncode,
                changed_files=AnyThing(),
                error=AnyThing(),
                stdin=stdin,
                stdout=stdout,
                term_columns=terminal_width,
            )

        last_pytest_stdout = stdout.value
        last_pytest_command = display_command

        if "fix" in flags:
            next_outcomes: Store[Dict[str, int]]
            example.run_pytest(outcomes=(next_outcomes := Store()))
            assert "errors" not in next_outcomes.value

        return {
            "cli_flags": cli_flags,
            "code": code,
            "example": example,
            "flags": flags,
            "options": options,
            "outcomes": outcomes,
            "stdin_options": stdin_options,
        }

    def run_header(code_header: str, line: int) -> Optional[str]:
        if last_code is None:
            raise AssertionError(
                f"{file}:{line - 1}: inline-snapshot-run needs a previous code block"
            )  # pragma: no cover

        print(f"test run line {line - 1}")
        result = run_example(
            last_code, code_header.removeprefix("inline-snapshot-run:").strip()
        )
        if result is None:
            return None  # pragma: no cover

        cli_flags = result["cli_flags"]
        options = result["options"]
        outcomes = result["outcomes"]
        stdin_options = result["stdin_options"]

        return "inline-snapshot-run: " + " ".join(
            sorted(cli_flags)
            + sorted(options & {"requires_assert"})
            + sorted(stdin_options)
            + [
                f"outcome-{k}={v}"
                for k, v in outcomes.value.items()
                if k in ("failed", "errors", "passed")
            ]
        )

    def test_block(block: Block):
        nonlocal last_code

        if block.code_header is None:
            last_code = block.code
            return block

        if block.code_header.startswith("inline-snapshot-lib:"):
            name = block.code_header.split()[1]
            extra_files[name].append(block.code)
            block.block_options["title"] = name
            return block

        if block.code_header.startswith("inline-snapshot-lib-set:"):
            name = block.code_header.split()[1]
            extra_files[name] = [block.code]
            block.block_options["title"] = name
            return block

        if block.code_header.startswith("todo-inline-snapshot:"):
            return block

        print(f"test block line {block.line}")

        code = block.code

        result = run_example(code, block.code_header, block)
        if result is None:
            return block

        cli_flags = result["cli_flags"]
        code = result["code"]
        example = result["example"]
        flags = result["flags"]
        options = result["options"]
        outcomes = result["outcomes"]
        stdin_options = result["stdin_options"]

        print("flags:", flags, repr(block.block_options))

        new_code = code
        if flags:
            new_code = example.read_file("tests/test_example.py")
        new_code.replace("\n\n", "\n")

        print("new code:")
        print(new_code)
        print("expected code:")
        print(code)

        block.code_header = "inline-snapshot: " + " ".join(
            sorted(cli_flags)
            + sorted(options & {"first_block", "requires_assert"})
            + sorted(stdin_options)
            + [
                f"outcome-{k}={v}"
                for k, v in outcomes.value.items()
                if k in ("failed", "errors", "passed")
            ]
        )

        linenum = 1

        if last_code is not None and "first_block" not in options:
            changed_lines = []
            alignment = align(last_code.split("\n"), new_code.split("\n"))
            for c in alignment:
                if c == "d":
                    continue
                elif c == "m":
                    linenum += 1
                else:
                    changed_lines.append(str(linenum))
                    linenum += 1
            if changed_lines:
                block.block_options["hl_lines"] = " ".join(changed_lines)
            else:
                pass  # pragma: no cover

        if "first_block" not in options:
            new_code = re.sub(r" *# *\(\d+\)\!?", "", new_code)

        block.code = new_code

        last_code = code
        return block

    map_code_blocks(file, test_block, map_last_output, run_header)


if __name__ == "__main__":  # pragma: no cover
    import sys

    file = Path(sys.argv[1])

    print(file)

    file_test(file, width=60)
