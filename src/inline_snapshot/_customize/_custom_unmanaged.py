from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Generator

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._change import ChangeBase

from ._custom import Custom


@dataclass()
class CustomUnmanaged(Custom):
    value: Any

    def _code_repr(
        self, context: AdapterContext
    ) -> Generator[ChangeBase, None, str]:  # pragma: no cover
        yield from ()
        return "'unmanaged'"

    def _map(self, f):
        return f(self.value)
