from __future__ import annotations

import ast

from inline_snapshot._adapter.adapter import AdapterContext
from inline_snapshot._change import CallArg
from inline_snapshot._change import ExternalChange
from inline_snapshot._change import Replace
from inline_snapshot._exceptions import UsageError
from inline_snapshot._external._format._protocol import get_format_handler
from inline_snapshot._external._format._protocol import get_format_handler_from_suffix
from inline_snapshot._external._outsource import Outsourced
from inline_snapshot._global_state import state
from inline_snapshot._inline_snapshot import create_snapshot
from inline_snapshot._unmanaged import declare_unmanaged

from .._snapshot.generic_value import GenericValue
from ._external_location import ExternalLocation


def external(name: str | None = None):
    return create_snapshot(External, name)


@declare_unmanaged
class External:
    def __init__(self, name: str, expr, context: AdapterContext):
        """External objects are used to move some data outside the source code.
        You should not instantiate this class directly, but by using `external()` instead.

        The location where the external data is stored can be defined by the storage protocol.
        The format is defined by the suffix.

        Parameters:
            name: the name of the external stored object which has the form "<hash>:<name>.<suffix>".
        """

        self._expr = expr
        self._context = context
        self._original_name = name

        self._location = ExternalLocation.from_name(name, context=context)
        self._original_location = ExternalLocation.from_name(name, context=context)

        self._value_changed = False

    def result(self):
        return self

    @classmethod
    def create_raw(cls, obj, context: AdapterContext):
        return cls._load_value_from_location(
            ExternalLocation.from_name(obj, context=context)
        )

    def _changes(self):
        if self._expr is None:
            node = None
        else:
            node = self._expr.node
            assert isinstance(node, ast.Call)

        new_name = self._location.to_str()
        if new_name != self._original_name:
            if self._original_name is None:
                yield CallArg(
                    "create",
                    self._context.file,
                    node,
                    0,
                    None,
                    f'"{new_name}"',
                    new_name,
                )

            else:
                yield Replace(
                    (
                        ("fix" if self._original_location.stem else "create")
                        if self._value_changed
                        else "update"
                    ),
                    self._context.file,
                    node.args[0] if node else None,
                    f'"{new_name}"',
                    self._original_name,
                    new_name,
                )

        if self._value_changed:
            yield ExternalChange(
                "fix" if self._original_location.stem else "create",
                self._tmp_file,
                self._original_location,
                self._location,
                get_format_handler_from_suffix(self._location.suffix or ""),
            )

    def __repr__(self):
        """Returns the representation of the external object.

        The length of the hash can be specified in the
        [config](configuration.md).
        """

        return f'external("{self._original_location.to_str()}")'

    @property
    def storage(self):
        storage_name = self._location.storage or state().default_storage

        return state().all_storages[storage_name]

    def _assign(self, other):
        format = get_format_handler(other, self._location.suffix)

        if not self._location.suffix:
            self._location.suffix = format.suffix

        self._tmp_file = state().new_tmp_path(self._location.suffix)

        format.encode(other, self._tmp_file)
        self._location = self.storage.new_location(self._location, self._tmp_file)

        self._value_changed = True

    def __eq__(self, other):
        """Two external objects are equal if they have the same value"""

        if isinstance(other, Outsourced):
            self._location.suffix = other._location.suffix
            other = other.data

        if isinstance(other, External):
            raise UsageError("you can not compare external(...) with external(...)")

        if isinstance(other, GenericValue):
            raise UsageError("you can not compare external(...) with snapshot(...)")

        if not self._original_location.stem:
            self._assign(other)
            state().missing_values += 1
            if state().update_flags.create:
                return True
            return False

        assert self._location.stem

        value = self._load_value()
        result = value == other

        if state().update_flags.fix or state().update_flags.update:
            if not result:
                self._assign(other)
                state().incorrect_values += 1
            return True

        return result

    def _load_value(self):
        return self._load_value_from_location(self._original_location)

    @classmethod
    def _load_value_from_location(cls, location: ExternalLocation) -> object:
        assert location.storage

        if not location.stem:
            raise UsageError(
                f"can not load external object from an non existing location {location.to_str()!r}"
            )
        storage = state().all_storages[location.storage]

        with storage.load(location) as f:
            assert location.suffix
            format = get_format_handler_from_suffix(location.suffix)

            return format.decode(f)
