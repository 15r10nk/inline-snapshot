import typing
from typing import TYPE_CHECKING

from inline_snapshot._unmanaged import declare_unmanaged

from ._global_state import state

if TYPE_CHECKING:

    T = typing.TypeVar("T")

    def Is(v: T) -> T:
        return v

else:

    class IsMetaType(type):
        def __call__(self, value):
            if not state().active:
                return value
            return super().__call__(value)

    @declare_unmanaged
    class Is(metaclass=IsMetaType):
        def __init__(self, value):
            self.value = value

        def __eq__(self, other):
            return self.value == other

        def __repr__(self):
            return repr(self.value)
