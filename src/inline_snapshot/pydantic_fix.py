from ._types import Snapshot

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

    if not pydantic.version.VERSION.startswith("1."):
        return

    origin_eq = BaseModel.__eq__

    def new_eq(self, other):
        if isinstance(other, Snapshot):  # type: ignore
            return other == self
        else:
            return origin_eq(self, other)

    BaseModel.__eq__ = new_eq
