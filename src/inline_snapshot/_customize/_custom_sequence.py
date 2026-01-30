from __future__ import annotations

import ast
from dataclasses import dataclass
from dataclasses import field
from typing import Generator

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._change import ChangeBase

from ._custom import Custom


class CustomSequenceTypes:
    trailing_comma: bool
    braces: str
    value_type: type


@dataclass(frozen=True)
class CustomSequence(Custom, CustomSequenceTypes):
    value: list[Custom] = field(compare=False)

    def _map(self, f):
        return f(self.value_type([x._map(f) for x in self.value]))

    def _code_repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        values = []
        for v in self.value:
            value = yield from v._code_repr(context)
            values.append(value)

        trailing_comma = self.trailing_comma and len(self.value) == 1
        return f"{self.braces[0]}{', '.join(values)}{', ' if trailing_comma else ''}{self.braces[1]}"


class CustomList(CustomSequence):
    node_type = ast.List
    value_type = list
    braces = "[]"
    trailing_comma = False


class CustomTuple(CustomSequence):
    node_type = ast.Tuple
    value_type = tuple
    braces = "()"
    trailing_comma = True
