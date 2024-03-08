import ast
from dataclasses import dataclass
from typing import Any
from typing import List
from typing import Optional
from typing import Tuple

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
