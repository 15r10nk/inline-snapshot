import re
import textwrap
from pathlib import Path

import inline_snapshot._inline_snapshot
import pytest


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
    """Test code blocks with the header <!-- inline-snapshot: options ... -->

    where options can be:
        * flags passed to --inline-snapshot=...
        * `this` to specify that the input source code should be the current block and not the last
        * `outcome-passed=2` to check for the pytest test outcome
    """
    block_start = re.compile("( *)``` *python")
    block_end = re.compile("```.*")

    header = re.compile("<!-- inline-snapshot:(.*)-->")

    text = file.read_text("utf-8")
    new_lines = []
    block_lines = []
    options = set()
    is_block = False
    code = None
    indent = ""

    project.pyproject(
        """
[tool.black]
line-length=80
"""
    )

    for linenumber, line in enumerate(text.splitlines(), start=1):
        m = block_start.fullmatch(line)
        if m and is_block == True:
            indent = m[1]
            block_lines = []
            new_lines.append(line)
            continue

        if block_end.fullmatch(line.strip()) and is_block:
            with subtests.test(line=linenumber):
                is_block = False

                last_code = code
                code = "\n".join(block_lines) + "\n"
                code = textwrap.dedent(code)

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

                if "show_error" in options:
                    new_code = new_code.split("# Error:")[0]
                    new_code += "# Error:" + textwrap.indent(result.errorLines(), "# ")

                if (
                    inline_snapshot._inline_snapshot._update_flags.fix
                ):  # pragma: no cover
                    new_lines.append(textwrap.indent(new_code.rstrip("\n"), indent))
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
                            if k in ("failed", "errors", "passed")
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
        file.write_text("\n".join(new_lines) + "\n", "utf-8")
