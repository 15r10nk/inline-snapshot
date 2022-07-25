from __future__ import annotations

import ast
import contextlib
import pathlib
from collections import defaultdict
from dataclasses import dataclass

import asttokens.util

try:
    from itertools import pairwise
except ImportError:
    from itertools import tee

    def pairwise(iterable):  # type: ignore
        a, b = tee(iterable)
        next(b, None)
        return zip(a, b)


# copied from pathlib to support python < 3.9
def is_relative_to(path, *other):
    """Return True if the path is relative to another path or False."""
    try:
        path.relative_to(*other)
        return True
    except ValueError:
        return False


@dataclass(order=True)
class SourcePosition:
    lineno: int
    col_offset: int


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


def filename_of(obj):
    if hasattr(obj, "filename"):
        return obj.filename

    return None


def start_of(obj) -> SourcePosition:

    if isinstance(obj, asttokens.util.Token):
        return SourcePosition(lineno=obj.start[0], col_offset=obj.start[1])

    if isinstance(obj, SourcePosition):
        return obj

    if isinstance(obj, ast.AST):
        return SourcePosition(lineno=obj.lineno, col_offset=obj.col_offset)

    if isinstance(obj, SourceRange):
        return obj.start

    if isinstance(obj, tuple) and len(obj) == 2:
        return SourcePosition(lineno=obj[0], col_offset=obj[1])

    return None


def end_of(obj) -> SourcePosition:
    if isinstance(obj, asttokens.util.Token):
        return SourcePosition(lineno=obj.end[0], col_offset=obj.end[1])

    if isinstance(obj, ast.AST):
        return SourcePosition(lineno=obj.lineno, end_col_offset=obj.end_col_offset)

    if isinstance(obj, SourceRange):
        return obj.end

    return start_of(obj)


def range_of(obj, end=None):
    if isinstance(obj, tuple) and len(obj) == 2 and end is None:
        return SourceRange(start_of(obj[0]), end_of(obj[1]))

    if end is None:
        end = obj
    return SourceRange(start_of(obj), end_of(end))


class Change:  # ChangeSet
    _next_change_id = 0

    def __init__(self, change_recorder=None):
        self.change_recorder = change_recorder or ChangeRecorder.current
        if self.change_recorder is None:
            raise UsageError(
                "A change set needs a change recorder. Pass one as argument or use ChangeRecorder.activate"
            )

        self.change_recorder._changes.append(self)

        self.change_id = self._next_change_id
        self._tags = []
        type(self)._next_change_id += 1

    def set_tags(self, *tags):
        self._tags = tags

    def replace(self, node, new_contend, *, filename=None):
        if filename is None:
            filename = filename_of(node)

        if isinstance(new_contend, ast.AST):
            new_contend = ast.unparse(new_contend)

        if not isinstance(new_contend, str):
            new_contend = repr(new_contend)

        self._replace(
            filename,
            range_of(node),
            new_contend,
        )

    def delete(self, node, *, filename=None):
        self.replace(node, "", filename=filename)

    def insert(self, node, new_content, *, filename=None):
        self.replace(start_of(node), new_content, filename=filename)

    def _replace(self, filename, range, new_contend):

        if isinstance(new_contend, ast.AST):
            new_contend = ast.unparse(new_contend)

        self.change_recorder.get_source(filename).replacements.append(
            Replacement(range=range, text=new_contend, change_id=self.change_id)
        )


class SourceFile:
    def __init__(self, filename):
        self.replacements = []
        self.filename = filename

    def rewrite(self):
        new_code = self.new_code()

        if new_code is not None:
            with open(self.filename, "bw") as code:
                code.write(new_code.encode())

    def new_code(self):
        """returns the new file contend or None if there are no replacepents to
        apply."""
        replacements = list(self.replacements)
        replacements.sort()

        for r in replacements:
            assert r.range.start <= r.range.end

        # TODO check for overlapping replacements
        for lhs, rhs in pairwise(replacements):
            assert lhs.range.end <= rhs.range.start

        if not replacements:
            return

        with open(self.filename, newline="") as code:
            code = code.read()

        new_code = ""
        last_i = 0
        add_end = True

        for pos, i, c in code_stream(code):
            if replacements:
                r = replacements[0]
                if pos == r.range.start:
                    new_code += code[last_i:i] + r.text
                    add_end = False
                if pos == r.range.end:
                    last_i = i
                    add_end = True
                    replacements.pop(0)
            else:
                break

        if add_end:
            new_code += code[last_i:]

        return new_code

    def generate_patch(self, basedir):
        """yields lines of a pathfile."""

        filename = self.filename
        if is_relative_to(filename, basedir):
            filename = filename.relative_to(basedir)

        with open(self.filename, newline="") as code:
            old_code = code.read().splitlines(keepends=True)

        new_code = self.new_code().splitlines(keepends=True)

        import difflib

        yield from difflib.unified_diff(
            old_code, new_code, fromfile=str(filename), tofile=str(filename)
        )


def get_source_file(filename):
    filename = pathlib.Path(filename)
    return ChangeRecorder.current.get_source(filename)


def replace(node, new_contend):
    Change().replace(node, new_contend)


def insert_before(node, new_contend):
    if isinstance(new_contend, ast.AST):
        new_contend = ast.unparse(new_contend)
    new_contend += "\n"

    _replace(
        node.filename,
        (node.lineno, node.col_offset),
        (node.lineno, node.col_offset),
        new_contend,
    )


@contextlib.contextmanager
def code_change_disabled():
    with ChangeRecorder().activate():
        yield


class ChangeRecorder:
    current: ChangeRecorder | None = None

    def __init__(self):

        self._source_files = defaultdict(SourceFile)
        self._changes = []

    @contextlib.contextmanager
    def activate(self):
        old_recorder = ChangeRecorder.current
        ChangeRecorder.current = self
        yield self
        ChangeRecorder.current = old_recorder

    def get_source(self, filename):

        filename = pathlib.Path(filename)
        if filename not in self._source_files:
            self._source_files[filename] = SourceFile(filename)

        return self._source_files[filename]

    def change_set(self):
        return Change(self)

    def new_change(self):
        return Change(self)

    def changes(self):
        return list(self._changes)

    def num_fixes(self):
        changes = set()
        for file in self._source_files.values():
            changes.update(change.change_id for change in file.replacements)
        return len(changes)

    def fix_all(self, tags=()):
        for file in self._source_files.values():
            file.rewrite()

    def generate_patchfile(self, filename):
        with open(filename, "w") as patch:
            for line in self.generate_patch(filename.parent):
                patch.write(line)

    def generate_patch(self, basedir):
        for file in self._source_files.values():
            if is_relative_to(file.filename, basedir):
                yield from file.generate_patch(basedir)

    def dump(self):
        for file in self._source_files.values():
            print("file:", file.filename)
            for change in file.replacements:
                print("  change:", change)


global_recorder = ChangeRecorder()
ChangeRecorder.current = global_recorder


def code_stream(source):
    idx = 0
    p_line = 1
    p_col = 0
    while idx < len(source):
        c = source[idx]
        if c == "\r" and idx + 1 < len(source) and source[idx + 1] == "\n":
            # \r\n
            yield SourcePosition(p_line, p_col), idx, "\r\n"
            idx += 1
            p_line += 1
            p_col = 0
        elif c in "\r\n":
            # \r or \n
            yield SourcePosition(p_line, p_col), idx, c
            p_line += 1
            p_col = 0
        else:
            yield SourcePosition(p_line, p_col), idx, c
            p_col += 1
        idx += 1


def rewrite(filename=None):

    if filename is None:
        for file in ChangeRecorder.current._source_files.values:
            file.rewrite()
    else:
        if filename in ChangeRecorder.current._source_files:
            ChangeRecorder.current._source_files[filename].rewrite()
