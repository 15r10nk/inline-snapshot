from inline_snapshot import snapshot
from inline_snapshot.testing import Example


def test_pydantic_repr(pydantic_version):

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
    ).run_pytest(
        ["--inline-snapshot=create"],
        extra_dependencies=[pydantic_version],
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
    ).run_pytest()
