from dataclasses import dataclass
from typing import Any
from typing import Generator

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._change import ChangeBase
from inline_snapshot._customize._custom import Custom


@dataclass(frozen=True, eq=False)
class Uncustomized(Custom):
    _value: Any

    def _map(self, f):
        return self._value

    def _code_repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        assert False
        return "<uncustomized>"
        yield
