from __future__ import annotations

import ast

from inline_snapshot._adapter.adapter import AdapterContext
from inline_snapshot._change import CallArg
from inline_snapshot._change import Replace
from inline_snapshot._exceptions import UsageError
from inline_snapshot._external._external_base import ExternalBase
from inline_snapshot._external._format._protocol import get_format_handler
from inline_snapshot._external._format._protocol import get_format_handler_from_suffix
from inline_snapshot._global_state import state
from inline_snapshot._inline_snapshot import create_snapshot
from inline_snapshot._unmanaged import declare_unmanaged

from ._external_location import ExternalLocation


def external(name: str | None = None):
    return create_snapshot(External, name)


@declare_unmanaged
class External(ExternalBase):
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

        super().__init__()

    def result(self):
        return self

    @classmethod
    def create_raw(cls, obj, context: AdapterContext):
        return cls._load_value_from_location(
            ExternalLocation.from_name(obj, context=context)
        )

    @property
    def _format(self):
        return get_format_handler_from_suffix(self._location.suffix or "")

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
                        if self._tmp_file is not None
                        else "update"
                    ),
                    self._context.file,
                    node.args[0] if node else None,
                    f'"{new_name}"',
                    self._original_name,
                    new_name,
                )

        yield from super()._changes()

    def _is_empty(self):
        return not self._original_location.stem

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
