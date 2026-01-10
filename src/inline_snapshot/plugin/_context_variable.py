from dataclasses import dataclass
from typing import Any


@dataclass
class ContextVariable:
    """
    representation of a value in the local or global context of a snapshot.

    This type can also be returned in an customize function and is then converted into an [Custom][inline_snapshot.Custom] object by an other Function
    """

    name: str
    "the name of the variable"

    value: Any
    "the value of the variable"
