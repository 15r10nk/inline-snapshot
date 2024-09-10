import platform
import re
import sys
import textwrap
from pathlib import Path

import inline_snapshot._inline_snapshot
import pytest


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="\\r in stdout can cause problems in snapshot strings",
)
@pytest.mark.skipif(
    sys.version_info[:2] != (3, 12),
    reason="\\r in stdout can cause problems in snapshot strings",
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
def test_docs(project, file, subtests):
    """Test code blocks with the header <!-- inline-snapshot: options ... -->

    where options can be:
        * flags passed to --inline-snapshot=...
        * `first_block` to specify that the input source code should be the current block and not the last
        * `outcome-passed=2` to check for the pytest test outcome
    """

    block_start = re.compile("( *)``` *python.*")
    block_end = re.compile("```.*")

    header = re.compile("<!-- inline-snapshot:(.*)-->")

    text = file.read_text("utf-8")
    new_lines = []
    block_lines = []
    options = set()
    is_block = False
    code = None
    indent = ""
    first_block = True

    project.pyproject(
        """
[tool.black]
line-length=80
"""
    )

    for linenumber, line in enumerate(text.splitlines(), start=1):
        m = block_start.fullmatch(line)
        if m and is_block == True:
            block_start_line = line
            indent = m[1]
            block_lines = []
            continue

        if block_end.fullmatch(line.strip()) and is_block:
            with subtests.test(line=linenumber):
                is_block = False

                last_code = code
                code = "\n".join(block_lines) + "\n"
                code = textwrap.dedent(code)
                if file.suffix == ".py":
                    code = code.replace("\\\\", "\\")

                flags = options & {"fix", "update", "create", "trim"}

                args = ["--inline-snapshot", ",".join(flags)] if flags else []

                if flags and "first_block" not in options:
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
                    new_code += "# Error:\n" + textwrap.indent(
                        result.errorLines(), "# "
                    )

                print("new code:")
                print(new_code)
                print("expected code:")
                print(code)

                if (
                    inline_snapshot._inline_snapshot._update_flags.fix
                ):  # pragma: no cover
                    flags_str = " ".join(
                        sorted(flags)
                        + sorted(options & {"first_block", "show_error"})
                        + [
                            f"outcome-{k}={v}"
                            for k, v in result.parseoutcomes().items()
                            if k in ("failed", "errors", "passed")
                        ]
                    )
                    header_line = f"{indent}<!-- inline-snapshot: {flags_str} -->"

                new_lines.append(header_line)

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
                        hl_lines = f' hl_lines="{" ".join(changed_lines)}"'
                    else:
                        assert False, "no lines changed"

                new_lines.append(f"{indent}``` python{hl_lines}")

                if (
                    inline_snapshot._inline_snapshot._update_flags.fix
                ):  # pragma: no cover
                    new_code = new_code.rstrip("\n")
                    if file.suffix == ".py":
                        new_code = new_code.replace("\\", "\\\\")
                    new_code = textwrap.indent(new_code, indent)

                    new_lines.append(new_code)
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
            if first_block:
                options.add("first_block")
                first_block = False
            header_line = line
            is_block = True

        if is_block:
            block_lines.append(line)
        else:
            new_lines.append(line)

    if inline_snapshot._inline_snapshot._update_flags.fix:  # pragma: no cover
        file.write_text("\n".join(new_lines) + "\n", "utf-8")
