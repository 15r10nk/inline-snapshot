from dataclasses import dataclass
from typing import Any


@dataclass
class ContextValue:
    name: str
    value: Any
