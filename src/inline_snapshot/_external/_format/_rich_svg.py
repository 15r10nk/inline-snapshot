from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.text import Text

from inline_snapshot._exceptions import UsageError
from inline_snapshot._external._diff import diff

from ._protocol import Format
from ._protocol import register_format

RICH_MARKUP_TAG = "inline-snapshot-rich-markup"
SVG_NAMESPACE = "http://www.w3.org/2000/svg"

ET.register_namespace("", SVG_NAMESPACE)


@dataclass
class RichSnapshot:
    """
    represents rich text as markup.
    This class stores two thinks:

    * the svg which is can be stored in an external file with `rich_snapshot == external()`
    * and the markup which is also stored as metadata in this file and is used for comparison.

    This allows you to mask specific parts in your code and show the original output at the same time, which is very useful when you want to test terminal output in your docs.

    """

    svg: str
    markup: str

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RichSnapshot):
            return NotImplemented
        return self.markup == other.markup

    def __repr__(self):
        return f"RichSnapshot({self.markup!r})"

    @staticmethod
    def from_console(console: Console, title="Terminal", include_styles=True):
        return RichSnapshot(
            svg=console.export_svg(title=title, clear=False),
            markup=Text.from_ansi(console.export_text(styles=include_styles)).markup,
        )

    def mask(self, regex):
        return RichSnapshot(svg=self.svg, markup=re.sub(regex, "", self.markup))


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _encode_markup(markup: str) -> str:
    return json.dumps(markup.splitlines(keepends=True), ensure_ascii=False, indent=2)


def _decode_markup(markup: str) -> str:
    try:
        lines = json.loads(markup)
    except json.JSONDecodeError as error:
        raise UsageError(
            f"Could not parse Rich SVG markup metadata: {error}"
        ) from error

    if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines):
        raise UsageError("Rich SVG markup metadata must be a list of strings.")

    return "".join(lines)


def _svg_with_metadata(snapshot: RichSnapshot) -> str:
    root = ET.fromstring(snapshot.svg)

    assert _local_name(root.tag) == "svg"

    metadata = ET.Element("metadata")
    markup = ET.SubElement(metadata, RICH_MARKUP_TAG)
    markup.text = _encode_markup(snapshot.markup)
    root.insert(0, metadata)

    return ET.tostring(root, encoding="unicode", short_empty_elements=False)


def _decode_rich_svg(text: str) -> RichSnapshot:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        raise UsageError(f"Could not parse Rich SVG metadata: {error}") from error

    for element in root.iter():
        if _local_name(element.tag) == RICH_MARKUP_TAG:
            return RichSnapshot(svg=text, markup=_decode_markup(element.text or "[]"))

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
        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(_svg_with_metadata(value))

    def decode(self, path: Path) -> RichSnapshot:
        return _decode_rich_svg(path.read_text(encoding="utf-8"))
