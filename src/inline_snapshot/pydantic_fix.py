from inline_snapshot.matcher import IsPydanticAttributes

from ._types import SnapshotBase

is_fixed = False


def pydantic_fix():
    global is_fixed
    if is_fixed:
        return  # pragma: no cover
    is_fixed = True

    try:
        from pydantic import BaseModel
    except ImportError:  # pragma: no cover
        return

    import pydantic

    if pydantic.version.VERSION.startswith("1."):

        origin_eq = BaseModel.__eq__

        def new_eq(self, other):
            if isinstance(other, (SnapshotBase, IsPydanticAttributes)):  # type: ignore
                return other == self
            else:
                return origin_eq(self, other)

        BaseModel.__eq__ = new_eq
