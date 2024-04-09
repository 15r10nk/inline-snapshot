import ast
import inspect
from dataclasses import dataclass


class Location:
    pass


@dataclass
class PositionalArgument(Location):
    position: int
    node: ast.FunctionDef
    signature: inspect.Signature


class KeywordArgument(Location):
    keyword: str
    node: ast.FunctionDef
    signature: inspect.Signature


class ListIndex(Location):
    node: ast.List
    index: int


class DictEntry(Location):
    node: ast.Dict
    key_pos: int
