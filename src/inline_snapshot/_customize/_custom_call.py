from __future__ import annotations

import ast
from dataclasses import dataclass
from dataclasses import field
from typing import Generator

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._change import ChangeBase

from ._custom import Custom


@dataclass(frozen=True)
class CustomDefault(Custom):
    value: Custom = field(compare=False)

    def _code_repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        yield from ()  # pragma: no cover
        # this should never be called because default values are never converted into code
        assert False

    def _map(self, f):
        return self.value._map(f)


def unwrap_default(value):
    if isinstance(value, CustomDefault):
        return value.value
    return value


@dataclass(frozen=True)
class CustomCall(Custom):
    node_type = ast.Call
    function: Custom = field(compare=False)
    args: list[Custom] = field(compare=False)
    kwargs: dict[str, Custom] = field(compare=False)

    def _code_repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        args = []
        for a in self.args:
            code = yield from a._code_repr(context)
            args.append(code)

        for k, v in self.kwargs.items():
            if not isinstance(v, CustomDefault):
                code = yield from v._code_repr(context)
                args.append(f"{k}={code}")

        return f"{yield from self.function._code_repr(context)}({', '.join(args)})"

    def argument(self, pos_or_str):
        if isinstance(pos_or_str, int):
            return unwrap_default(self.args[pos_or_str])
        else:
            return unwrap_default(self.kwargs[pos_or_str])

    def _map(self, f):
        return self.function._map(f)(
            *[f(x._map(f)) for x in self.args],
            **{k: f(v._map(f)) for k, v in self.kwargs.items()},
        )
