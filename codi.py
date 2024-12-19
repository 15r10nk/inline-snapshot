from inline_snapshot import snapshot
from pydantic import BaseModel


class M(BaseModel):
    a: int


def test():
    assert M(a=5) == snapshot()
