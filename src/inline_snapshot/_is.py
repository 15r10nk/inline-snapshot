import typing
from typing import TYPE_CHECKING

if TYPE_CHECKING:

    T = typing.TypeVar("T")

    def Is(v: T) -> T:
        return v

else:

    class Is:
        def __init__(self, value):
            self.value = value

        def __eq__(self, other):
            return self.value == other

        def __repr__(self):
            return repr(self.value)
