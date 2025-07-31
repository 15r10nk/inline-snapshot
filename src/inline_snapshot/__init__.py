from inline_snapshot._external._diff import BinaryDiff
from inline_snapshot._external._diff import TextDiff

from ._code_repr import HasRepr
from ._code_repr import customize_repr
from ._exceptions import UsageError
from ._external._external import external
from ._external._external_file import external_file
from ._external._format._protocol import Format
from ._external._format._protocol import register_format
from ._external._format._protocol import register_format_alias
from ._external._outsource import outsource
from ._inline_snapshot import snapshot
from ._is import Is
from ._types import Category
from ._types import Snapshot

__all__ = [
    "snapshot",
    "external",
    "outsource",
    "customize_repr",
    "HasRepr",
    "Is",
    "Category",
    "Snapshot",
    "UsageError",
    "register_format_alias",
    "register_format",
    "Format",
    "TextDiff",
    "BinaryDiff",
    "external_file",
]

__version__ = "0.26.0"
