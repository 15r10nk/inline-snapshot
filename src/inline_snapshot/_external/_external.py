from __future__ import annotations

import ast
import inspect
from pathlib import Path
from types import FrameType

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._change import CallArg
from inline_snapshot._change import Replace
from inline_snapshot._exceptions import UsageError
from inline_snapshot._external._external_base import ExternalBase
from inline_snapshot._external._external_base import ExternalBaseData
from inline_snapshot._external._format._protocol import get_format_handler
from inline_snapshot._external._format._protocol import get_format_handler_from_suffix
from inline_snapshot._external._storage._protocol import StorageLookupError
from inline_snapshot._global_state import state
from inline_snapshot._types import snapshot_key
from inline_snapshot._unmanaged import declare_unmanaged

from ._external_location import ExternalLocation


def external(name: str | None = None):
    frame = inspect.currentframe()
    assert frame is not None
    frame = frame.f_back
    assert frame is not None

    if not state().active:
        return External.create_raw(name, frame)

    key = snapshot_key(frame)
    context = AdapterContext(frame)
    data = state().snapshots.get(key)
    if not isinstance(data, ExternalData):
        data = ExternalData.from_name(name, context)
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
    ) -> None:
        super().__init__(
            original_location=original_location,
            location=location,
        )
        self.original_name = original_name
        self.filename = filename

    @classmethod
    def from_name(cls, name: str | None, context: AdapterContext) -> ExternalData:
        location = ExternalLocation.from_name(name, context=context)
        return cls(
            original_name=name,
            original_location=ExternalLocation.from_name(name, context=context),
            location=location,
            filename=Path(context.file.filename),
        )

    def __repr__(self) -> str:
        return f'external("{self.original_location.to_str()}")'


@declare_unmanaged
class External(ExternalBase):
    _context: AdapterContext

    def __init__(self, context: AdapterContext, data: ExternalData):
        """External objects are used to move some data outside the source code.
        You should not instantiate this class directly, but by using `external()` instead.

        The location where the external data is stored can be defined by the storage protocol.
        The format is defined by the suffix.
        """

        self._context = context
        self._data = data

    @property
    def _original_name(self):
        return self._data.original_name

    @classmethod
    def create_raw(cls, obj, frame: FrameType):
        context = AdapterContext(frame)
        return cls._load_value_from_location(
            ExternalLocation.from_name(obj, context=context)
        )

    @property
    def _format(self):
        return get_format_handler_from_suffix(self._location.suffix or "")

    def _changes(self):

        node = self._context.expr.node

        if node is not None:
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

    def _load_value(self, which):
        if which == "new":
            if self._tmp_file:
                format = get_format_handler_from_suffix(self._location.suffix)
                return format.decode(self._tmp_file)
            else:
                raise StorageLookupError("no new value", files=[])
        if which == "old":
            location = self._original_location
            if not location.exists():
                raise StorageLookupError("no old value", files=[])

            return self._load_value_from_location(location)

        assert False, f"which has to be new or old but is {which!r}"

    @classmethod
    def _load_value_from_location(cls, location: ExternalLocation) -> object:
        assert location.storage

        if not location.stem:
            raise UsageError(
                f"cannot load external object from a non-existing location {location.to_str()!r}"
            )
        storage = state().all_storages[location.storage]

        with storage.load(location) as f:
            assert location.suffix
            format = get_format_handler_from_suffix(location.suffix)

            return format.decode(f)
