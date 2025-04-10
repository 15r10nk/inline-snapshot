from ._code_repr import HasRepr
from ._code_repr import customize_repr
from ._exceptions import UsageError
from ._external import external
from ._external._external import outsource
from ._external._external import txt_like_suffix
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
    "txt_like_suffix",
]

__version__ = "0.22.0"
