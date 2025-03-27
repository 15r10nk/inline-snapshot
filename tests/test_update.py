import sys

from inline_snapshot import snapshot
from inline_snapshot.testing._example import Example

executable = sys.executable.replace("\\", "\\\\")


def test_no_reported_updates():

    Example(
        {
            "fmt_cmd.py": """\
from sys import stdin

text=stdin.read()
text=text.replace("8","4+4")
print(text,end="")
""",
            "pyproject.toml": f"""\
[tool.inline-snapshot]
format-command="{executable} fmt_cmd.py {{filename}}"
""",
            "test_a.py": """\
from inline_snapshot import snapshot

def test_a():
    assert 2**3 == snapshot(4+4)
""",
        }
    ).run_pytest(
        ["--inline-snapshot=report"],
        changed_files=snapshot({}),
        report=snapshot(""),
    )
