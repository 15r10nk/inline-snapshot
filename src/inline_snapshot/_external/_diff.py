from difflib import unified_diff
from itertools import islice
from pathlib import Path

from rich.syntax import Syntax


def textDiff(original: Path, new: Path):

    original_text = original.read_text("utf-8")
    new_text = new.read_text("utf-8")

    diff = "\n".join(
        islice(
            unified_diff(original_text.splitlines(), new_text.splitlines()),
            2,
            None,
        )
    ).strip()

    return Syntax(diff, "diff", theme="ansi_light", word_wrap=True)


def binaryDiff(original: Path, new: Path):
    return "todo"
