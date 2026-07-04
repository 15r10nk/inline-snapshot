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
    unique_id: str | None = None,
) -> RichSnapshot:
    rich_text = Text.from_ansi(text)

    console = Console(file=io.StringIO(), record=True, width=width)
    console.print(rich_text, end="")

    return RichSnapshot(
        svg=console.export_svg(title=title, unique_id=unique_id),
        markup=rich_text.markup,
    )
