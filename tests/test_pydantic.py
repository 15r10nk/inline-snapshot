import sys

import pydantic
import pytest

from inline_snapshot import snapshot
from inline_snapshot.testing import Example


def test_pydantic_create_snapshot():

    Example(
        """
from pydantic import BaseModel
from inline_snapshot import snapshot

class M(BaseModel):
    size:int
    name:str
    age:int=4

def test_pydantic():
    m=M(size=5,name="Tom")
    assert m==snapshot()
    assert m.dict()==snapshot()

    """
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\

from pydantic import BaseModel
from inline_snapshot import snapshot

class M(BaseModel):
    size:int
    name:str
    age:int=4

def test_pydantic():
    m=M(size=5,name="Tom")
    assert m==snapshot(M(size=5, name="Tom"))
    assert m.dict()==snapshot({"size": 5, "name": "Tom", "age": 4})

    \
"""
            }
        ),
    ).run_inline(
        ["--inline-snapshot=disable"], reported_categories=set()
    )


def test_pydantic_field_repr():

    Example(
        """\
from inline_snapshot import snapshot
from pydantic import BaseModel,Field

class container(BaseModel):
    a: int
    b: int = Field(default=5,repr=False)

def test():
    assert container(a=1,b=5) == snapshot()
"""
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot
from pydantic import BaseModel,Field

class container(BaseModel):
    a: int
    b: int = Field(default=5,repr=False)

def test():
    assert container(a=1,b=5) == snapshot(container(a=1))
"""
            }
        ),
    ).run_inline(
        ["--inline-snapshot=disable"], reported_categories=set()
    )


def test_pydantic_default_value():
    Example(
        """\
from inline_snapshot import snapshot,Is
from dataclasses import dataclass,field
from pydantic import BaseModel,Field

class A(BaseModel):
    a:int
    b:int=2
    c:list=Field(default_factory=list)

def test_something():
    assert A(a=1) == snapshot(A(a=1,b=2,c=[]))
"""
    ).run_inline(
        ["--inline-snapshot=update"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot,Is
from dataclasses import dataclass,field
from pydantic import BaseModel,Field

class A(BaseModel):
    a:int
    b:int=2
    c:list=Field(default_factory=list)

def test_something():
    assert A(a=1) == snapshot(A(a=1))
"""
            }
        ),
    )


def test_pydantic_evaluate_twice():
    Example(
        """\
from inline_snapshot import snapshot
from pydantic import BaseModel

class A(BaseModel):
    a:int

def test_something():
    for _ in [1,2]:
        assert A(a=1) == snapshot(A(a=1))
"""
    ).run_inline(
        changed_files=snapshot({}),
    )


def test_pydantic_factory_method():
    Example(
        """\
from inline_snapshot import snapshot
from pydantic import BaseModel

class A(BaseModel):
    a:int

    @classmethod
    def from_str(cls,s):
        return cls(a=int(s))

def test_something():
    for a in [1,2]:
        assert A(a=2) == snapshot(A.from_str("1"))
"""
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot
from pydantic import BaseModel

class A(BaseModel):
    a:int

    @classmethod
    def from_str(cls,s):
        return cls(a=int(s))

def test_something():
    for a in [1,2]:
        assert A(a=2) == snapshot(A(a=2))
"""
            }
        ),
    )


@pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="NewType is a function in 3.9 and cannot be checked with isinstance or serialized to code",
)
def test_pydantic_newtype():
    Example(
        """\
from typing import NewType
from pydantic import BaseModel
from inline_snapshot import snapshot


def test_something():
    SomeID = NewType("SomeID", int)

    class Something(BaseModel):
        some_id: SomeID
    a = Something(some_id=SomeID(1))
    assert a == snapshot()
"""
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from typing import NewType
from pydantic import BaseModel
from inline_snapshot import snapshot


def test_something():
    SomeID = NewType("SomeID", int)

    class Something(BaseModel):
        some_id: SomeID
    a = Something(some_id=SomeID(1))
    assert a == snapshot(Something(some_id=SomeID(1)))
"""
            }
        ),
    ).run_inline()


@pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="NewType is a function in 3.9 and cannot be checked with isinstance or serialized to code",
)
def test_pydantic_newtype_import():
    Example(
        {
            "some_id.py": """\
from typing import NewType
from pydantic import BaseModel
from inline_snapshot import snapshot

SomeID = NewType("SomeID", int)

class Something(BaseModel):
    some_id1: SomeID
    some_id2: SomeID=SomeID(5)


def create():
    return Something(some_id1=SomeID(1),some_id2=SomeID(5))
                """,
            "test_something.py": """\
from inline_snapshot import snapshot
from some_id import create

def test_something():
    assert create() == snapshot()
""",
        }
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from inline_snapshot import snapshot
from some_id import create

from some_id import SomeID
from some_id import Something

def test_something():
    assert create() == snapshot(Something(some_id1=SomeID(1)))
"""
            }
        ),
    ).run_inline()


@pytest.mark.skipif(
    pydantic.version.VERSION.startswith("1."),
    reason="pydantic 1 cannot compare C[int]() with C()",
)
def test_pydantic_generic_class():
    Example(
        """\
from typing import Generic, TypeVar
from inline_snapshot import snapshot
from pydantic import BaseModel

I=TypeVar("I")
class C(BaseModel,Generic[I]):
    a:int

def test_a():
    c=C[int](a=5)

    assert c == snapshot()
"""
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from typing import Generic, TypeVar
from inline_snapshot import snapshot
from pydantic import BaseModel

I=TypeVar("I")
class C(BaseModel,Generic[I]):
    a:int

def test_a():
    c=C[int](a=5)

    assert c == snapshot(C(a=5))
"""
            }
        ),
    ).run_inline(
        reported_categories={"update"}
    )
