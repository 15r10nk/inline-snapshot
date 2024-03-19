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

from asttokens import ASTTokens
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


def extend_comma(atok: ASTTokens, start: Token, end: Token) -> Tuple[Token, Token]:
    # prev = atok.prev_token(start)
    # if prev.string == ",":
    #    return prev, end

    next = atok.next_token(end)
    if next.string == ",":
        return start, next

    return start, end


@dataclass()
class Delete(Change):
    node: ast.AST
    old_value: Any

    def apply(self):
        change = ChangeRecorder.current.new_change()
        parent = self.node.parent
        atok = self.source.asttokens()
        if isinstance(parent, ast.Dict):
            index = parent.values.index(self.node)
            key = parent.keys[index]

            start, *_ = atok.get_tokens(key)
            *_, end = atok.get_tokens(self.node)

            start, end = extend_comma(atok, start, end)

            change.replace((start, end), "", filename=self.filename)
        else:
            assert False


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

    def apply(self):
        change = ChangeRecorder.current.new_change()
        atok = self.source.asttokens()
        code = ",".join(f"{k}:{v}" for k, v in self.new_code)

        if self.position == len(self.node.keys):
            *_, token = atok.get_tokens(self.node.values[-1])
            token = atok.next_token(token)
            code = ", " + code
        else:
            token, *_ = atok.get_tokens(self.node.keys[self.position])
            code = code + ", "

        change.insert(token, code, filename=self.filename)


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


def apply_all(all_changes: List[Change]):
    by_parent: Dict[EnhancedAST, List[Union[Delete, DictInsert, ListInsert]]] = (
        defaultdict(list)
    )
    sources = {}

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
        print(parent, changes)

        rec = ChangeRecorder.current.new_change()
        if isinstance(parent, (ast.List, ast.Tuple)):
            to_delete = {
                change.node for change in changes if isinstance(change, Delete)
            }
            to_insert = {
                change.position: change
                for change in changes
                if isinstance(change, ListInsert)
            }

            new_code = []
            deleted = False
            last_token, *_, end_token = source.asttokens().get_tokens(parent)
            is_start = True
            elements = 0

            for index, entry in enumerate(parent.elts):
                if index in to_insert:
                    new_code += to_insert[index].new_code
                    print("insert", entry, new_code)
                if entry in to_delete:
                    deleted = True
                    print("delete1", entry)
                else:
                    entry_tokens = list(source.asttokens().get_tokens(entry))
                    first_token = entry_tokens[0]
                    new_last_token = entry_tokens[-1]
                    elements += len(new_code) + 1

                    if deleted or new_code:
                        print("change", deleted, new_code)

                        code = ""
                        if new_code:
                            code = ", ".join(new_code) + ", "
                        if not is_start:
                            code = ", " + code
                        print("code", code)

                        rec.replace(
                            (end_of(last_token), start_of(first_token)),
                            code,
                            filename=source.filename,
                        )
                    print("keep", entry)
                    new_code = []
                    deleted = False
                    last_token = new_last_token
                    is_start = False

            if len(parent.elts) in to_insert:
                new_code += to_insert[len(parent.elts)].new_code
                elements += len(new_code)

            if new_code or deleted or elements == 1 or len(parent.elts) <= 1:
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

        else:
            for change in changes:
                change.apply()
