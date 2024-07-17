from typing import Literal
from typing import TypeVar

from typing_extensions import Annotated

T = TypeVar("T")

Snapshot = Annotated[T, "just an alias"]


Category = Literal["update", "fix", "create", "trim"]
