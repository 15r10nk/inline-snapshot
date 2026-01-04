from __future__ import annotations

from typing import Generator

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._change import ChangeBase
from inline_snapshot._sentinels import undefined

from ._custom import Custom


class CustomUndefined(Custom):
    def __init__(self):
        self.value = undefined

    def repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        yield from ()
        return "..."

    def map(self, f):
        return f(undefined)
