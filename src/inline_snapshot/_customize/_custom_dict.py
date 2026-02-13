from __future__ import annotations

import ast
from dataclasses import dataclass
from dataclasses import field
from typing import Generator

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._change import ChangeBase

from ._custom import Custom


@dataclass(frozen=True)
class CustomDict(Custom):
    node_type = ast.Dict
    value: dict[Custom, Custom] = field(compare=False)

    def _map(self, f):
        return f({k._map(f): v._map(f) for k, v in self.value.items()})

    def _code_repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        values = []
        for k, v in self.value.items():
            key = yield from k._code_repr(context)
            value = yield from v._code_repr(context)
            values.append(f"{key}: {value}")

        return f"{{{ ', '.join(values)}}}"
