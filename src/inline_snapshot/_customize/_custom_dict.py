from __future__ import annotations

import ast
from dataclasses import dataclass
from dataclasses import field
from typing import Generator

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._change import ChangeBase

from ._custom import Custom


@dataclass()
class CustomDict(Custom):
    node_type = ast.Dict
    value: dict[Custom, Custom] = field(compare=False)

    def map(self, f):
        return f({k.map(f): v.map(f) for k, v in self.value.items()})

    def repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        values = []
        for k, v in self.value.items():
            key = yield from k.repr(context)
            value = yield from v.repr(context)
            values.append(f"{key}: {value}")

        return f"{{{ ', '.join(values)}}}"

    def _needed_imports(self):
        for k, v in self.value.items():
            yield from k._needed_imports()
            yield from v._needed_imports()
