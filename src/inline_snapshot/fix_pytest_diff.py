from typing import IO
from typing import Any
from typing import Set

from inline_snapshot._is import Is
from inline_snapshot._snapshot.generic_value import GenericValue
from inline_snapshot._unmanaged import Unmanaged


def fix_pytest_diff():
    from _pytest._io.pprint import PrettyPrinter

    def _pprint_snapshot(
        self,
        object: Any,
        stream: IO[str],
        indent: int,
        allowance: int,
        context: Set[int],
        level: int,
    ) -> None:
        self._format(object._old_value, stream, indent, allowance, context, level)

    PrettyPrinter._dispatch[GenericValue.__repr__] = _pprint_snapshot

    def _pprint_unmanaged(
        self,
        object: Any,
        stream: IO[str],
        indent: int,
        allowance: int,
        context: Set[int],
        level: int,
    ) -> None:
        self._format(object.value, stream, indent, allowance, context, level)

    PrettyPrinter._dispatch[Unmanaged.__repr__] = _pprint_unmanaged

    def _pprint_is(
        self,
        object: Any,
        stream: IO[str],
        indent: int,
        allowance: int,
        context: Set[int],
        level: int,
    ) -> None:
        self._format(object.value, stream, indent, allowance, context, level)

    PrettyPrinter._dispatch[Is.__repr__] = _pprint_is
