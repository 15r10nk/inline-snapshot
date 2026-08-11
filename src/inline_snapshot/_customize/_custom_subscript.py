from __future__ import annotations

import ast
from dataclasses import dataclass
from dataclasses import field
from typing import Generator

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._change import ChangeBase

from ._custom import Custom


@dataclass(frozen=True)
class CustomSubscript(Custom):
    node_type = ast.Subscript
    obj: Custom = field(compare=False)
    index: Custom = field(compare=False)

    def _code_repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        obj_code = yield from self.obj._code_repr(context)
        index_code = yield from self.index._code_repr(context)
        return f"{obj_code}[{index_code}]"

    def _map(self, f):
        return self.obj._map(f)[f(self.index._map(f))]
