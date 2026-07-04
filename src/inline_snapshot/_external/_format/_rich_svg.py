from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from inline_snapshot._exceptions import UsageError
from inline_snapshot._external._diff import diff

from ._protocol import Format
from ._protocol import register_format

RICH_MARKUP_TAG = "inline-snapshot-rich-markup"


@dataclass
class RichSnapshot:
    svg: str
    markup: str

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RichSnapshot):
            return NotImplemented
        return self.markup == other.markup


def _metadata(markup: str) -> str:
    return (
        "<metadata>\n"
        f"<{RICH_MARKUP_TAG}>"
        f"{html.escape(markup, quote=False)}"
        f"</{RICH_MARKUP_TAG}>\n"
        "</metadata>"
    )


def _svg_with_metadata(snapshot: RichSnapshot) -> str:
    svg = re.sub(
        rf"\s*<metadata>\s*<{RICH_MARKUP_TAG}>.*?</{RICH_MARKUP_TAG}>\s*</metadata>",
        "",
        snapshot.svg,
        count=1,
        flags=re.DOTALL,
    )

    svg_start = svg.find(">")
    if svg_start == -1 or "<svg" not in svg[:svg_start]:
        raise UsageError("RichSnapshot.svg does not contain an SVG root element.")

    return f"{svg[: svg_start + 1]}\n{_metadata(snapshot.markup)}{svg[svg_start + 1:]}"


def _decode_rich_svg(text: str) -> RichSnapshot:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        raise UsageError(f"Could not parse Rich SVG metadata: {error}") from error

    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == RICH_MARKUP_TAG:
            return RichSnapshot(svg=text, markup=element.text or "")

    raise UsageError("Rich SVG file does not contain inline-snapshot rich markup.")


@register_format
class RichSvgFormat(Format[RichSnapshot]):
    "Stores rich terminal snapshots as SVG files with embedded markup."

    suffix = ".rich.svg"

    def rich_diff(self, original: Path, new: Path):
        return diff(self.decode(original).markup, self.decode(new).markup)

    def rich_show(self, path: Path):
        return self.decode(path).markup

    def is_format_for(self, value: object):
        return isinstance(value, RichSnapshot)

    def encode(self, value: RichSnapshot, path: Path):
        path.write_text(_svg_with_metadata(value), encoding="utf-8", newline="\n")

    def decode(self, path: Path) -> RichSnapshot:
        return _decode_rich_svg(path.read_text(encoding="utf-8"))
