from __future__ import annotations

import io

from rich.console import Console
from rich.text import Text

from inline_snapshot._external._format._rich_svg import RichSnapshot


def render_ansi_to_svg(
    text: str,
    *,
    width: int,
    title: str,
    prompt: str | None = None,
) -> RichSnapshot:
    console = Console(file=io.StringIO(), record=True, width=width)
    if prompt is not None:
        console.print(prompt)

    rich_text = Text.from_ansi(text)

    console.print(rich_text, end="")

    return RichSnapshot.from_console(console, title=title)
