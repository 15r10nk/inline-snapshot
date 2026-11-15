"""Public API for customizing snapshots and registering storage backends."""

from ._core._external._external_location import ExternalLocation
from ._core._external._storage._protocol import Storage
from ._core._external._storage._protocol import StorageLookupError
from ._core._external._storage._value import StorageValue
from ._core.plugin import Builder
from ._core.plugin import Custom
from ._core.plugin import Import
from ._core.plugin import ImportFrom
from ._core.plugin import InlineSnapshotPluginSpec
from ._core.plugin import customize
from ._core.plugin import hookimpl

__all__ = (
    "ExternalLocation",
    "Storage",
    "StorageValue",
    "StorageLookupError",
    "InlineSnapshotPluginSpec",
    "customize",
    "hookimpl",
    "Builder",
    "Custom",
    "Import",
    "ImportFrom",
)
