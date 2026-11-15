from dataclasses import dataclass
from typing import Any
from typing import Generator

from inline_snapshot._core._change import ChangeBase
from inline_snapshot._core._customize._custom import Custom
from inline_snapshot._core._snapshot_context import SnapshotContext


@dataclass(frozen=True, eq=False)
class Uncustomized(Custom):
    _value: Any

    def __post_init__(self):
        assert not isinstance(self._value, Custom)

    def _map(self, f):
        return self._value

    def _code_repr(self, context: SnapshotContext) -> Generator[ChangeBase, None, str]:
        assert False
        return "<uncustomized>"
        yield

    def __repr__(self):
        return repr(self._value)
