import ast
from collections import defaultdict
from dataclasses import dataclass
from typing import Any
from typing import cast
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from asttokens.util import Token
from executing.executing import EnhancedAST
from executing.executing import Source

from ._rewrite_code import ChangeRecorder
from ._rewrite_code import end_of
from ._rewrite_code import start_of


@dataclass()
class Change:
    flag: str
    source: Source

    @property
    def filename(self):
        return self.source.filename

    def apply(self):
        raise NotImplementedError()


@dataclass()
class Delete(Change):
    node: ast.AST
    old_value: Any


@dataclass()
class AddArgument(Change):
    node: ast.Call

    position: Optional[int]
    name: Optional[str]

    new_code: str
    new_value: Any


@dataclass()
class ListInsert(Change):
    node: ast.List
    position: int

    new_code: List[str]
    new_values: List[Any]


@dataclass()
class DictInsert(Change):
    node: ast.Dict
    position: int

    new_code: List[Tuple[str, str]]
    new_values: List[Tuple[Any, Any]]


@dataclass()
class Replace(Change):
    node: ast.AST

    new_code: str
    old_value: Any
    new_value: Any

    def apply(self):
        change = ChangeRecorder.current.new_change()
        range = self.source.asttokens().get_text_positions(self.node, False)
        change.replace(range, self.new_code, filename=self.filename)


@dataclass()
class CallArg(Change):
    node: Optional[ast.Call]
    arg_pos: Optional[int]
    arg_name: Optional[str]

    new_code: str
    old_value: Any
    new_value: Any

    def apply(self):
        change = ChangeRecorder.current.new_change()
        tokens = list(self.source.asttokens().get_tokens(self.node))

        call = self.node
        tokens = list(self.source.asttokens().get_tokens(call))

        assert isinstance(call, ast.Call)
        assert len(call.args) == 0
        assert len(call.keywords) == 0
        assert tokens[-2].string == "("
        assert tokens[-1].string == ")"

        assert self.arg_pos == 0
        assert self.arg_name == None

        change = ChangeRecorder.current.new_change()
        change.set_tags("inline_snapshot")
        change.replace(
            (end_of(tokens[-2]), start_of(tokens[-1])),
            self.new_code,
            filename=self.filename,
        )


TokenRange = Tuple[Token, Token]


def generic_sequence_update(
    source: Source,
    parent: Union[ast.List, ast.Tuple, ast.Dict],
    parent_elements: List[Union[TokenRange, None]],
    to_insert: Dict[int, List[str]],
):
    rec = ChangeRecorder.current.new_change()

    new_code = []
    deleted = False
    last_token, *_, end_token = source.asttokens().get_tokens(parent)
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
            # trailing comma for tuples (1,)i
            code += ","

        rec.replace(
            (end_of(last_token), start_of(end_token)),
            code,
            filename=source.filename,
        )


def apply_all(all_changes: List[Change]):
    by_parent: Dict[EnhancedAST, List[Union[Delete, DictInsert, ListInsert]]] = (
        defaultdict(list)
    )
    sources: Dict[EnhancedAST, Source] = {}

    for change in all_changes:
        if isinstance(change, Delete):
            node = cast(EnhancedAST, change.node).parent
            by_parent[node].append(change)
            sources[node] = change.source

        elif isinstance(change, (DictInsert, ListInsert)):
            node = cast(EnhancedAST, change.node)
            by_parent[node].append(change)
            sources[node] = change.source
        else:
            change.apply()

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
                [None if e in to_delete else list_token_range(e) for e in parent.elts],
                to_insert,
            )

        elif isinstance(parent, (ast.Dict)):
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
                [
                    None if value in to_delete else dict_token_range(key, value)
                    for key, value in zip(parent.keys, parent.values)
                ],
                to_insert,
            )

        else:
            assert False, parent
