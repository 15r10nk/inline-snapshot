from ._code_repr import register_repr
from ._external import external
from ._external import outsource
from ._inline_snapshot import snapshot

__all__ = ["snapshot", "external", "outsource", "register_repr"]

__version__ = "0.10.2"
