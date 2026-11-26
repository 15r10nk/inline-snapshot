from __future__ import annotations

import ast
import inspect
from pathlib import Path
from types import CodeType

from inline_snapshot._core._change import CallArg
from inline_snapshot._core._change import Replace
from inline_snapshot._core._external._external_base import ExternalBase
from inline_snapshot._core._external._external_base import ExternalBaseData
from inline_snapshot._core._external._format._protocol import (
    get_format_handler_from_suffix,
)
from inline_snapshot._core._external._storage._protocol import Storage
from inline_snapshot._core._external._storage._protocol import StorageLookupError
from inline_snapshot._core._external._storage._value import StorageValue
from inline_snapshot._core._global_state import state
from inline_snapshot._core._snapshot_context import SnapshotContext
from inline_snapshot._core._types import snapshot_key
from inline_snapshot._core._unmanaged import declare_unmanaged

from ._external_comparison import ExternalComparison
from ._external_location import ExternalLocation
from ._external_value import load_external_value


def external(name: str | None = None):
    frame = inspect.currentframe()
    assert frame is not None
    frame = frame.f_back
    assert frame is not None

    context = SnapshotContext(frame)
    if not state().active:
        location = ExternalLocation._from_name(name, context=context)
        storage = state().all_storages[location.storage]
        if type(storage).lazy_compare is not Storage.lazy_compare:
            return ExternalComparison(location, storage)
        return load_external_value(location)

    key = snapshot_key(frame)
    data = state().snapshots.get(key)
    if not isinstance(data, ExternalData):
        data = ExternalData.from_name(name, context, frame.f_code)
        state().snapshots[key] = data

    return External(context, data)


class ExternalData(ExternalBaseData):
    """Frame-free state shared by evaluations of one external call site."""

    original_location: ExternalLocation
    location: ExternalLocation

    def __init__(
        self,
        *,
        original_name: str | None,
        original_location: ExternalLocation,
        location: ExternalLocation,
        filename: Path,
        code: CodeType,
    ) -> None:
        super().__init__(
            original_location=original_location,
            location=location,
        )
        self.original_name = original_name
        self.filename = filename
        # Prevent reuse of the id(frame.f_code) component in snapshot_key().
        self.code = code

    @classmethod
    def from_name(
        cls, name: str | None, context: SnapshotContext, code: CodeType
    ) -> ExternalData:
        location = ExternalLocation._from_name(name, context=context)
        return cls(
            original_name=name,
            original_location=ExternalLocation._from_name(name, context=context),
            location=location,
            filename=Path(context.file.filename),
            code=code,
        )

    def __repr__(self) -> str:
        return f'external("{self.original_location.to_str()}")'


@declare_unmanaged
class External(ExternalBase):
    _context: SnapshotContext

    def __init__(self, context: SnapshotContext, data: ExternalData):
        """External objects are used to move some data outside the source code.
        You should not instantiate this class directly, but by using `external()` instead.

        The location where the external data is stored can be defined by the storage protocol.
        The format is defined by the suffix.
        """

        self._context = context
        self._data = data

    @property
    def _format(self):
        return get_format_handler_from_suffix(self._data.location.suffix or "")

    def _changes(self):

        node = self._context.expr.node

        if node is not None:
            assert isinstance(node, ast.Call)

        new_name = self._data.location.to_str()
        if new_name != self._data.original_name:
            if self._data.original_name is None:
                yield CallArg(
                    "create",
                    self._context.file,
                    node,
                    0,
                    None,
                    f'"{new_name}"',
                )

            else:
                yield Replace(
                    (
                        ("fix" if self._data.original_location.stem else "create")
                        if self._data.tmp_file is not None
                        else "update"
                    ),
                    self._context.file,
                    node.args[0] if node else None,
                    f'"{new_name}"',
                )

        yield from super()._changes()

    def _is_empty(self):
        return not self._data.original_location.stem

    def __repr__(self):
        """Returns the representation of the external object.

        The length of the hash can be specified in the
        [config](configuration.md).
        """

        return f'external("{self._data.original_location.to_str()}")'

    @property
    def storage(self):
        storage_name = self._data.location.storage or state().default_storage

        return state().all_storages[storage_name]

    def _prepare_value(self, other):
        return StorageValue(other, self._data.location)

    def _compare_value(self, other: StorageValue):
        if type(self.storage).lazy_compare is not Storage.lazy_compare:
            return self.storage.lazy_compare(self._data.original_location, other)
        return super()._compare_value(other.value)

    def _assign(self, other: StorageValue):
        self._data.tmp_file = other.data
        self._data.location = self.storage.new_location(
            self._data.location, self._data.tmp_file
        )

    def _load_value(self, which):
        if which == "new":
            if self._data.tmp_file:
                format = get_format_handler_from_suffix(self._data.location.suffix)
                return format.decode(self._data.tmp_file)
            else:
                raise StorageLookupError("no new value", files=[])
        if which == "old":
            location = self._data.original_location
            if not location.exists():
                raise StorageLookupError("no old value", files=[])

            return load_external_value(location)

        assert False, f"which has to be new or old but is {which!r}"
