import itertools
import platform
import re
import sys
import textwrap
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from typing import Dict
from typing import Generic
from typing import List
from typing import Optional
from typing import TypeVar

import pytest
from executing import is_pytest_compatible

from inline_snapshot import snapshot
from inline_snapshot._external._external_file import external_file
from inline_snapshot._flags import Flags
from inline_snapshot._global_state import snapshot_env
from inline_snapshot.extra import raises
from inline_snapshot.testing import Example
from inline_snapshot.version import is_insider


@dataclass
class Block:
    code: str
    code_header: Optional[str]
    block_options: str
    line: int


def map_code_blocks(file: Path, func):

    block_start = re.compile("( *)``` *python(.*)")
    block_end = re.compile("```.*")

    header = re.compile("<!--(.*)-->")

    current_code = file.read_text("utf-8")
    new_lines = []
    block_lines: List[str] = []
    is_block = False
    code = None
    indent = ""
    block_start_linenum: Optional[int] = None
    block_options: Optional[str] = None
    code_header = None
    header_line = ""

    for linenumber, line in enumerate(current_code.splitlines(), start=1):
        m = block_start.fullmatch(line)
        if m and not is_block:
            # ``` python
            block_start_linenum = linenumber
            indent = m[1]
            block_options = m[2]
            block_lines = []
            is_block = True
            continue

        if block_end.fullmatch(line.strip()) and is_block:
            # ```
            is_block = False
            assert block_options is not None
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

            new_lines.append(
                f"{indent}``` {('python '+new_block.block_options.strip()).strip()}"
            )

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
            header_line = line
            code_header = m[1].strip()
            continue
        else:
            if header_line:
                new_lines.append(header_line)
                code_header = None
                header_line = ""

        new_lines.append(line)

    new_code = "\n".join(new_lines) + "\n"

    assert external_file(file, format=".txt") == new_code


def test_map_code_blocks(tmp_path):

    file = tmp_path / "example.md"

    def test_doc(
        markdown_code,
        handle_block=lambda block: exec(block.code),
        blocks=[],
        exception="<no exception>",
        new_markdown_code=None,
    ):

        file.write_bytes(markdown_code.encode("utf-8"))

        recorded_blocks = []

        with raises(exception):

            def test_block(block):
                handle_block(block)
                recorded_blocks.append(block)
                return block

            with snapshot_env() as state:
                state.update_flags.fix = True
                state.active = True

                map_code_blocks(file, test_block)

                for snapshot in state.snapshots.values():
                    for change in snapshot._changes():
                        change.apply_external_changes()

            assert recorded_blocks == blocks

            with snapshot_env():
                map_code_blocks(file, test_block)

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
                    code="print(1 + 1)\n", code_header=None, block_options="", line=2
                ),
                Block(
                    code="print(1 - 1)\n",
                    code_header="inline-snapshot: create test",
                    block_options=' hl_lines="1 2 3"',
                    line=7,
                ),
            ]
        ),
    )

    def change_block(block):
        block.code = "# removed"
        block.code_header = "header"
        block.block_options = "option a b c"

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
                    block_options="option a b c",
                    line=2,
                )
            ]
        ),
        new_markdown_code=snapshot(
            """\
text
<!-- header -->
``` python option a b c
# removed
```
"""
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
def test_docs(file, subtests):
    file_test(file, subtests)


T = TypeVar("T")


class Store(Generic[T]):
    value: T

    def __eq__(self, other: Any):
        self.value = other
        return True


def file_test(
    file: Path,
    subtests,
    width: int = 80,
    use_hl_lines: bool = True,
):
    """Test code blocks with the header <!-- inline-snapshot: options ... -->

    where options can be:
        * flags passed to --inline-snapshot=...
        * `first_block` to specify that the input source code should be the current block and not the last
        * `outcome-passed=2` to check for the pytest test outcome
    """

    last_code = None

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
from inline_snapshot import customize_repr

@customize_repr
def _(value:FakeDatetime):
    return value.__repr__().replace("FakeDatetime","datetime.datetime")

@customize_repr
def _(value:FakeDate):
    return value.__repr__().replace("FakeDate","datetime.date")


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

    def test_block(block: Block):
        if block.code_header is None:
            return block

        if block.code_header.startswith("inline-snapshot-lib:"):
            extra_files[block.code_header.split()[1]].append(block.code)
            return block

        if block.code_header.startswith("inline-snapshot-lib-set:"):
            extra_files[block.code_header.split()[1]] = [block.code]
            return block

        if block.code_header.startswith("todo-inline-snapshot:"):
            return block

        nonlocal last_code
        with subtests.test(line=block.line):
            print(f"test block line {block.line}")

            code = block.code

            options = set(block.code_header.split())

            if "requires_assert" in options and (
                not is_pytest_compatible() or not is_insider
            ):
                return block

            flags = options & Flags.all().to_set()

            args = ["--inline-snapshot", ",".join(flags)] if flags else []

            errors = Store[str]()
            outcomes = Store[Dict[str, int]]()
            returncode = Store[int]()

            if flags and "first_block" not in options:
                assert last_code is not None
                test_files = {"test_example.py": last_code}
            else:
                test_files = {"test_example.py": code}

            example = Example({**std_files, **test_files})
            if extra_files:
                all_files = [
                    [(key, file) for file in files]
                    for key, files in extra_files.items()
                ]
                for files in itertools.product(*all_files):
                    example = example.with_files(dict(files))

                    print("run with")
                    example = example.run_pytest(
                        args, error=errors, outcomes=outcomes, returncode=returncode
                    )

            else:
                example = example.run_pytest(
                    args, error=errors, outcomes=outcomes, returncode=returncode
                )

            print("flags:", flags, repr(block.block_options))

            new_code = code
            if flags:
                new_code = example.read_file("test_example.py")
            new_code.replace("\n\n", "\n")

            if "show_error" in options:
                new_code = new_code.split("# Error:")[0]
                new_code += "# Error:\n" + textwrap.indent(errors.value, "# ")

            print("new code:")
            print(new_code)
            print("expected code:")
            print(code)

            block.code_header = "inline-snapshot: " + " ".join(
                sorted(flags)
                + sorted(options & {"first_block", "show_error", "requires_assert"})
                + [
                    f"outcome-{k}={v}"
                    for k, v in outcomes.value.items()
                    if k in ("failed", "errors", "passed")
                ]
            )

            if use_hl_lines:
                from inline_snapshot._align import align

                linenum = 1
                hl_lines = ""

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
                        hl_lines = f'hl_lines="{" ".join(changed_lines)}"'
                    else:
                        assert False, "no lines changed"
                block.block_options = hl_lines
            else:
                pass  # pragma: no cover

            block.code = new_code

            last_code = code
        return block

    map_code_blocks(file, test_block)


if __name__ == "__main__":  # pragma: no cover
    import sys

    file = Path(sys.argv[1])

    print(file)

    @contextmanager
    def test(line):
        yield

    nosubtests = SimpleNamespace(test=test)

    file_test(file, nosubtests, width=60, use_hl_lines=True)
