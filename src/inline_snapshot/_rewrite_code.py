from __future__ import annotations

import logging
import pathlib
import sys
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from difflib import unified_diff
from itertools import islice

import asttokens.util
from asttokens import LineNumbers

from ._format import enforce_formatting
from ._format import format_code

if sys.version_info >= (3, 10):
    from itertools import pairwise
else:
    from itertools import tee

    def pairwise(iterable):  # type: ignore
        a, b = tee(iterable)
        next(b, None)
        return zip(a, b)


@dataclass(order=True)
class SourcePosition:
    lineno: int
    col_offset: int

    def offset(self, line_numbers):
        return line_numbers.line_to_offset(self.lineno, self.col_offset)


@dataclass(order=True)
class SourceRange:
    start: SourcePosition
    end: SourcePosition

    def __post_init__(self):
        if self.start > self.end:
            raise ValueError("range start should be lower then end")


@dataclass(order=True)
class Replacement:
    range: SourceRange
    text: str
    change_id: int = 0


def start_of(obj) -> SourcePosition:
    if isinstance(obj, asttokens.util.Token):
        return SourcePosition(lineno=obj.start[0], col_offset=obj.start[1])

    if isinstance(obj, SourcePosition):
        return obj

    if isinstance(obj, SourceRange):
        return obj.start

    if isinstance(obj, tuple) and len(obj) == 2:
        return SourcePosition(lineno=obj[0], col_offset=obj[1])

    assert False


def end_of(obj) -> SourcePosition:
    if isinstance(obj, asttokens.util.Token):
        return SourcePosition(lineno=obj.end[0], col_offset=obj.end[1])

    if isinstance(obj, SourceRange):
        return obj.end

    return start_of(obj)


def range_of(obj):
    if isinstance(obj, tuple) and len(obj) == 2:
        return SourceRange(start_of(obj[0]), end_of(obj[1]))

    return SourceRange(start_of(obj), end_of(obj))


class UsageError(Exception):
    pass


class Change:  # ChangeSet
    _next_change_id = 0

    def __init__(self, change_recorder):
        self.change_recorder = change_recorder

        self.change_recorder._changes.append(self)

        self.change_id = self._next_change_id
        type(self)._next_change_id += 1

    def replace(self, node, new_contend, *, filename):
        assert isinstance(new_contend, str)

        self._replace(
            filename,
            range_of(node),
            new_contend,
        )

    def delete(self, node, *, filename):
        self.replace(node, "", filename=filename)

    def insert(self, node, new_content, *, filename):
        self.replace(start_of(node), new_content, filename=filename)

    def _replace(self, filename, range, new_contend):
        source = self.change_recorder.get_source(filename)
        source.replacements.append(
            Replacement(range=range, text=new_contend, change_id=self.change_id)
        )
        source._check()


class SourceFile:
    def __init__(self, filename: pathlib.Path):
        self.replacements: list[Replacement] = []
        self.filename = filename
        self.source = self.filename.read_text("utf-8")

    def rewrite(self):
        new_code = self.new_code()

        with open(self.filename, "bw") as code:
            code.write(new_code.encode())

    def virtual_write(self):
        self.source = self.new_code()

    def _check(self):
        replacements = list(self.replacements)
        replacements.sort()

        for r in replacements:
            assert r.range.start <= r.range.end, r

        for lhs, rhs in pairwise(replacements):
            assert lhs.range.end <= rhs.range.start, (lhs, rhs)

    def new_code(self) -> str:
        """Returns the new file contend or None if there are no replacepents to
        apply."""
        replacements = list(self.replacements)
        replacements.sort()

        self._check()

        code = self.filename.read_text("utf-8")

        format_whole_file = enforce_formatting() or code == format_code(
            code, self.filename
        )

        if not format_whole_file:
            logging.info(f"file is not formatted with black: {self.filename}")
            import black

            logging.info(f"black version: {black.__version__}")

        line_numbers = LineNumbers(code)

        new_code = asttokens.util.replace(
            code,
            [
                (
                    r.range.start.offset(line_numbers),
                    r.range.end.offset(line_numbers),
                    r.text,
                )
                for r in replacements
            ],
        )

        if format_whole_file:
            new_code = format_code(new_code, self.filename)

        return new_code

    def diff(self):
        return "\n".join(
            islice(
                unified_diff(self.source.splitlines(), self.new_code().splitlines()),
                2,
                None,
            )
        ).strip()


class ChangeRecorder:

    def __init__(self):
        self._source_files = defaultdict(SourceFile)
        self._changes = []

    def get_source(self, filename) -> SourceFile:
        filename = pathlib.Path(filename)
        if filename not in self._source_files:
            self._source_files[filename] = SourceFile(filename)

        return self._source_files[filename]

    def files(self) -> Iterable[SourceFile]:
        return self._source_files.values()

    def new_change(self):
        return Change(self)

    def num_fixes(self):
        changes = set()
        for file in self._source_files.values():
            changes.update(change.change_id for change in file.replacements)
        return len(changes)

    def fix_all(self):
        for file in self._source_files.values():
            file.rewrite()

    def virtual_write(self):
        for file in self._source_files.values():
            file.virtual_write()

    def dump(self):  # pragma: no cover
        for file in self._source_files.values():
            print("file:", file.filename)
            for change in file.replacements:
                print("  change:", change)
