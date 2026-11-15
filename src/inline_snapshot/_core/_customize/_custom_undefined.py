from __future__ import annotations

from typing import Generator

from inline_snapshot._core._change import ChangeBase
from inline_snapshot._core._sentinels import undefined
from inline_snapshot._core._snapshot_context import SnapshotContext

from ._custom import Custom


class CustomUndefined(Custom):
    def __init__(self):
        self.value = undefined

    def _code_repr(self, context: SnapshotContext) -> Generator[ChangeBase, None, str]:
        yield from ()
        return "..."

    def _map(self, f):
        return f(undefined)
