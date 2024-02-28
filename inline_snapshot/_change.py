import ast
from dataclasses import dataclass
from typing import Any
from typing import Optional

from ._location import Location


@dataclass()
class Change:
    flag: str


@dataclass()
class Delete(Change):
    location: Location
    old_value: Any


@dataclass()
class Insert(Change):
    location: Location
    key_expr: Optional[ast.Expr]
    value_expr: ast.Expr

    old_value: Any
    new_value: Any


@dataclass()
class Replace(Change):
    location: Location
    value_expr: ast.Expr

    old_value: Any
    new_value: Any
