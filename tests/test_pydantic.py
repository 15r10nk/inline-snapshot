from inline_snapshot import snapshot
from inline_snapshot.testing import Example


def test_pydantic_repr():

    Example(
        """
from pydantic import BaseModel
from inline_snapshot import snapshot

class M(BaseModel):
    size:int
    name:str
    age:int=4

def test_pydantic():
    assert M(size=5,name="Tom")==snapshot()

    """
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "test_something.py": """\

from pydantic import BaseModel
from inline_snapshot import snapshot

class M(BaseModel):
    size:int
    name:str
    age:int=4

def test_pydantic():
    assert M(size=5,name="Tom")==snapshot(M(size=5, name="Tom"))

    \
"""
            }
        ),
    ).run_inline()
