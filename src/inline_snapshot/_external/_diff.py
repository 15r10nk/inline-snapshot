from difflib import unified_diff
from itertools import islice
from pathlib import Path

from rich.syntax import Syntax


def diff(original_text, new_text):

    diff = "\n".join(
        islice(
            unified_diff(original_text.splitlines(), new_text.splitlines()),
            2,
            None,
        )
    ).strip()

    return Syntax(diff, "diff", theme="ansi_light", word_wrap=True)


def hexdump(bytes, style=False):
    from binascii import hexlify

    result = []
    for i in range(0, len(bytes), 16):
        line = bytes[i : i + 16]
        if style:
            dot = "[white].[/white]"
        else:
            dot = "."

        s = "".join(chr(c) if 32 <= c < 127 else dot for c in line)
        if style:
            result.append(
                f"[dark_green]{i:08x}[/]: [bright_black]{hexlify(line,' ',-2).decode():<39}[/] |[orange3]{s}{' '*(16-len(line))}[/]|"
            )
        else:
            result.append(f"{i:08x}: {hexlify(line,' ',-2).decode():<39} |{s:<16}|")

    return "\n".join(result)


class TextDiff:
    def rich_diff(self, original: Path, new: Path):

        return diff(original.read_text("utf-8"), new.read_text("utf-8"))

    def rich_show(self, path: Path):
        return Syntax.from_path(str(path), theme="ansi_light", word_wrap=True)


class BinaryDiff:
    def rich_diff(self, original: Path, new: Path):

        original_bytes = original.read_bytes()
        new_bytes = new.read_bytes()

        return diff(hexdump(original_bytes), hexdump(new_bytes))

    def rich_show(self, path: Path):
        content = path.read_bytes()

        if len(content) > 20 * 16:
            return f"<binary file ({len(content)} bytes)>"
        else:
            return hexdump(content, style=True)
