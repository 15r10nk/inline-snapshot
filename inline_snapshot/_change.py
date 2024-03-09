import ast
from dataclasses import dataclass
from typing import Any
from typing import List
from typing import Optional
from typing import Tuple

from asttokens import ASTTokens
from asttokens.util import Token
from executing import Source

from ._rewrite_code import ChangeRecorder


@dataclass()
class Change:
    flag: str
    source: Source

    @property
    def filename(self):
        return self.source.filename

    def apply(self):
        pass


def extend_comma(atok: ASTTokens, start: Token, end: Token) -> Tuple[Token, Token]:
    prev = atok.prev_token(start)
    if prev.string == ",":
        return prev, end

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
