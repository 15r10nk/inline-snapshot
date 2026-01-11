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

    def repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        yield from ()  # pragma: no cover
        # this should never be called because default values are never converted into code
        assert False

    def _map(self, f):
        return self.value._map(f)

    def _needed_imports(self):
        yield from self.value._needed_imports()


def unwrap_default(value):
    if isinstance(value, CustomDefault):
        return value.value
    return value


@dataclass(frozen=True)
class CustomCall(Custom):
    node_type = ast.Call
    _function: Custom = field(compare=False)
    _args: list[Custom] = field(compare=False)
    _kwargs: dict[str, Custom] = field(compare=False)
    _kwonly: dict[str, Custom] = field(default_factory=dict, compare=False)

    def repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        args = []
        for a in self.args:
            v = yield from a.repr(context)
            args.append(v)

        for k, v in self.kwargs.items():
            if not isinstance(v, CustomDefault):
                value = yield from v.repr(context)
                args.append(f"{k}={value}")

        return f"{yield from self._function.repr(context)}({', '.join(args)})"

    @property
    def args(self):
        return self._args

    @property
    def all_pos_args(self):
        return [*self._args, *self._kwargs.values()]

    @property
    def kwargs(self):
        return {**self._kwargs, **self._kwonly}

    def argument(self, pos_or_str):
        if isinstance(pos_or_str, int):
            return unwrap_default(self.all_pos_args[pos_or_str])
        else:
            return unwrap_default(self.kwargs[pos_or_str])

    def _map(self, f):
        return self._function._map(f)(
            *[f(x._map(f)) for x in self._args],
            **{k: f(v._map(f)) for k, v in self.kwargs.items()},
        )

    def _needed_imports(self):
        yield from self._function._needed_imports()
        for v in self._args:
            yield from v._needed_imports()

        for v in self._kwargs.values():
            yield from v._needed_imports()

        for v in self._kwonly.values():
            yield from v._needed_imports()
