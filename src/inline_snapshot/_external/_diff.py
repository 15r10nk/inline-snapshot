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


def textDiff(original: Path, new: Path):

    return diff(original.read_text("utf-8"), new.read_text("utf-8"))


def hexdump(bytes):
    from binascii import hexlify

    result = []
    for i in range(0, len(bytes), 16):
        line = bytes[i : i + 16]
        s = "".join(chr(c) if 32 <= c < 127 else "." for c in line)
        result.append(f"{i:08x}: {hexlify(line,' ',-2).decode():<39} |{s:<16}|")

    return "\n".join(result)


def binaryDiff(original: Path, new: Path):

    original_bytes = original.read_bytes()
    new_bytes = new.read_bytes()

    return diff(hexdump(original_bytes), hexdump(new_bytes))
