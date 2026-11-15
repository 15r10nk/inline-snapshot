"""Core snapshot evaluation, customization, storage, and source rewriting."""

from ._code_repr import HasRepr
from ._code_repr import customize_repr
from ._exceptions import UsageError
from ._external._diff import BinaryDiff
from ._external._diff import TextDiff
from ._external._external import external
from ._external._external_file import external_file
from ._external._format._protocol import Format
from ._external._format._protocol import register_format
from ._external._format._protocol import register_format_alias
from ._external._outsource import outsource
from ._get_snapshot_value import get_snapshot_value
from ._inline_snapshot import snapshot
from ._is import Is
from ._snapshot_arg import snapshot_arg
from ._types import Category
from ._types import Snapshot
from ._types import SnapshotArg
from ._unmanaged import declare_unmanaged

__all__ = [
    "HasRepr",
    "customize_repr",
    "UsageError",
    "BinaryDiff",
    "TextDiff",
    "external",
    "external_file",
    "Format",
    "register_format",
    "register_format_alias",
    "outsource",
    "get_snapshot_value",
    "snapshot",
    "Is",
    "snapshot_arg",
    "Category",
    "Snapshot",
    "SnapshotArg",
    "declare_unmanaged",
]
