from __future__ import annotations

import ast
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import DefaultDict
from typing import Tuple
from typing import cast

from asttokens.util import Token
from executing.executing import EnhancedAST

from inline_snapshot._external._external_location import Location
from inline_snapshot._source_file import SourceFile

from ._rewrite_code import ChangeRecorder
from ._rewrite_code import end_of
from ._rewrite_code import start_of

if TYPE_CHECKING:
    from inline_snapshot._external._format._protocol import Format


class ChangeBase:
    flag: str

    def rich_diff(self):
        raise NotImplementedError

    def apply_external_changes(self):
        raise NotImplementedError

    def apply(self, recorder: ChangeRecorder):
        raise NotImplementedError


@dataclass()
class ExternalChange(ChangeBase):
    flag: str

    new_file: Path

    old_location: Location
    new_location: Location

    format: Format

    def rich_diff(self):

        title = str(self.new_location)
        if title != (old_name := str(self.old_location)) and self.old_location.stem:
            title = f"{old_name} -> {title}"

        if (
            self.old_location.exists()
            and self.old_location.suffix == self.new_location.suffix
        ):
            with self.old_location.load() as old_file:
                return title, self.format.rich_diff(old_file, self.new_file)
        else:
            return title, self.format.rich_show(self.new_file)

    def apply_external_changes(self):
        self.new_location.store(self.new_file)

    def apply(self, recorder: ChangeRecorder):
        pass


@dataclass()
class ExternalRemove(ChangeBase):
    flag: str

    old_location: Location

    def rich_diff(self):

        title = f"delete {self.old_location}"

        from inline_snapshot._external._format._protocol import (
            get_format_handler_from_suffix,
        )

        with self.old_location.load() as old_file:
            assert self.old_location.suffix
            format = get_format_handler_from_suffix(self.old_location.suffix)
            return title, format.rich_show(old_file)

    def apply_external_changes(self):
        self.old_location.delete()

    def apply(self, recorder: ChangeRecorder):
        pass


@dataclass()
class Change(ChangeBase):
    flag: str
    file: SourceFile

    def rich_diff(self):
        return None

    @property
    def filename(self):
        return self.file.filename

    def apply(self, recorder: ChangeRecorder):
        raise NotImplementedError()

    def apply_external_changes(self):
        pass


@dataclass()
class Delete(Change):
    node: ast.AST
    old_value: Any


@dataclass()
class AddArgument(Change):
    node: ast.Call

    position: int | None
    name: str | None

    new_code: str
    new_value: Any


@dataclass()
class ListInsert(Change):
    node: ast.List
    position: int

    new_code: list[str]
    new_values: list[Any]


@dataclass()
class DictInsert(Change):
    node: ast.Dict
    position: int

    new_code: list[tuple[str, str]]
    new_values: list[tuple[Any, Any]]


@dataclass()
class Replace(Change):
    node: ast.AST

    new_code: str
    old_value: Any
    new_value: Any

    def apply(self, recorder: ChangeRecorder):
        change = recorder.new_change()
        range = self.file.asttokens().get_text_positions(self.node, False)
        change.replace(range, self.new_code, filename=self.filename)


@dataclass()
class CallArg(Change):
    node: ast.Call | None
    arg_pos: int | None
    arg_name: str | None

    new_code: str
    new_value: Any


TokenRange = Tuple[Token, Token]


def brace_tokens(source, node) -> TokenRange:
    first_token, *_, end_token = source.asttokens().get_tokens(node)
    return first_token, end_token


def generic_sequence_update(
    source: SourceFile,
    parent: ast.List | ast.Tuple | ast.Dict | ast.Call,
    brace_tokens: TokenRange,
    parent_elements: list[TokenRange | None],
    to_insert: dict[int, list[str]],
    recorder: ChangeRecorder,
):
    rec = recorder.new_change()

    new_code = []
    deleted = False
    last_token, end_token = brace_tokens
    is_start = True
    elements = 0

    for index, entry in enumerate(parent_elements):
        if index in to_insert:
            new_code += to_insert[index]
        if entry is None:
            deleted = True
        else:
            first_token, new_last_token = entry
            elements += len(new_code) + 1

            if deleted or new_code:

                code = ""
                if new_code:
                    code = ", ".join(new_code) + ", "
                if not is_start:
                    code = ", " + code

                rec.replace(
                    (end_of(last_token), start_of(first_token)),
                    code,
                    filename=source.filename,
                )
            new_code = []
            deleted = False
            last_token = new_last_token
            is_start = False

    if len(parent_elements) in to_insert:
        new_code += to_insert[len(parent_elements)]
        elements += len(new_code)

    if new_code or deleted or elements == 1 or len(parent_elements) <= 1:
        code = ", ".join(new_code)
        if not is_start and code:
            code = ", " + code

        if elements == 1 and isinstance(parent, ast.Tuple):
            # trailing comma for tuples (1,)
            code += ","

        rec.replace(
            (end_of(last_token), start_of(end_token)),
            code,
            filename=source.filename,
        )


def apply_all(all_changes: list[ChangeBase], recorder: ChangeRecorder):
    by_parent: dict[EnhancedAST, list[Delete | DictInsert | ListInsert | CallArg]] = (
        defaultdict(list)
    )
    sources: dict[EnhancedAST, SourceFile] = {}

    for change in all_changes:
        if isinstance(change, Delete):
            node = cast(EnhancedAST, change.node).parent
            if isinstance(node, ast.keyword):
                node = node.parent
            by_parent[node].append(change)
            sources[node] = change.file

        elif isinstance(change, (DictInsert, ListInsert, CallArg)):
            node = cast(EnhancedAST, change.node)
            by_parent[node].append(change)
            sources[node] = change.file
        else:
            change.apply(recorder)

    for parent, changes in by_parent.items():
        source = sources[parent]

        if isinstance(parent, (ast.List, ast.Tuple)):
            to_delete = {
                change.node for change in changes if isinstance(change, Delete)
            }
            to_insert = {
                change.position: change.new_code
                for change in changes
                if isinstance(change, ListInsert)
            }

            def list_token_range(entry):
                r = list(source.asttokens().get_tokens(entry))
                return r[0], r[-1]

            generic_sequence_update(
                source,
                parent,
                brace_tokens(source, parent),
                [None if e in to_delete else list_token_range(e) for e in parent.elts],
                to_insert,
                recorder,
            )

        elif isinstance(parent, ast.Call):
            to_delete = {
                change.node for change in changes if isinstance(change, Delete)
            }
            atok = source.asttokens()

            def arg_token_range(node):
                if isinstance(node.parent, ast.keyword):
                    node = node.parent
                r = list(atok.get_tokens(node))
                return r[0], r[-1]

            braces_left = atok.next_token(list(atok.get_tokens(parent.func))[-1])
            assert braces_left.string == "("
            braces_right = list(atok.get_tokens(parent))[-1]
            assert braces_right.string == ")"

            to_insert = DefaultDict(list)

            for change in changes:
                if isinstance(change, CallArg):
                    if change.arg_name is not None:
                        position = (
                            change.arg_pos
                            if change.arg_pos is not None
                            else len(parent.args) + len(parent.keywords)
                        )
                        to_insert[position].append(
                            f"{change.arg_name} = {change.new_code}"
                        )
                    else:
                        assert change.arg_pos is not None
                        to_insert[change.arg_pos].append(change.new_code)

            generic_sequence_update(
                source,
                parent,
                (braces_left, braces_right),
                [
                    None if e in to_delete else arg_token_range(e)
                    for e in parent.args + [kw.value for kw in parent.keywords]
                ],
                to_insert,
                recorder,
            )

        elif isinstance(parent, ast.Dict):
            to_delete = {
                change.node for change in changes if isinstance(change, Delete)
            }
            to_insert = {
                change.position: [f"{key}: {value}" for key, value in change.new_code]
                for change in changes
                if isinstance(change, DictInsert)
            }

            def dict_token_range(key, value):
                return (
                    list(source.asttokens().get_tokens(key))[0],
                    list(source.asttokens().get_tokens(value))[-1],
                )

            generic_sequence_update(
                source,
                parent,
                brace_tokens(source, parent),
                [
                    None if value in to_delete else dict_token_range(key, value)
                    for key, value in zip(parent.keys, parent.values)
                ],
                to_insert,
                recorder,
            )

        else:
            assert False, parent
