import sys

import pydantic
import pytest

from inline_snapshot import Is
from inline_snapshot import snapshot
from inline_snapshot.testing import Example


def test_pydantic_create_snapshot():

    Example("""
from pydantic import BaseModel
from inline_snapshot import snapshot

class M(BaseModel):
    size:int
    name:str
    age:int=4

def test_pydantic():
    m=M(size=5,name="Tom")
    assert m==snapshot()

    """).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot({"tests/test_something.py": """\

from pydantic import BaseModel
from inline_snapshot import snapshot

class M(BaseModel):
    size:int
    name:str
    age:int=4

def test_pydantic():
    m=M(size=5,name="Tom")
    assert m==snapshot(M(size=5, name="Tom"))

    \
"""}),
    ).run_inline(["--inline-snapshot=disable"], reported_categories=set())


def test_pydantic_field_repr():

    Example("""\
from inline_snapshot import snapshot
from pydantic import BaseModel,Field

class container(BaseModel):
    a: int
    b: int = Field(default=5,repr=False)

def test():
    assert container(a=1,b=5) == snapshot()
""").run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot({"tests/test_something.py": """\
from inline_snapshot import snapshot
from pydantic import BaseModel,Field

class container(BaseModel):
    a: int
    b: int = Field(default=5,repr=False)

def test():
    assert container(a=1,b=5) == snapshot(container(a=1))
"""}),
    ).run_inline(["--inline-snapshot=disable"], reported_categories=set())


def test_pydantic_default_value():
    Example("""\
from inline_snapshot import snapshot,Is
from dataclasses import dataclass,field
from pydantic import BaseModel,Field

class A(BaseModel):
    a:int
    b:int=2
    c:list=Field(default_factory=list)

def test_something():
    assert A(a=1) == snapshot(A(a=1,b=2,c=[]))
""").run_inline(
        ["--inline-snapshot=update"],
        changed_files=snapshot({"tests/test_something.py": """\
from inline_snapshot import snapshot,Is
from dataclasses import dataclass,field
from pydantic import BaseModel,Field

class A(BaseModel):
    a:int
    b:int=2
    c:list=Field(default_factory=list)

def test_something():
    assert A(a=1) == snapshot(A(a=1))
"""}),
    )


def test_pydantic_evaluate_twice():
    Example("""\
from inline_snapshot import snapshot
from pydantic import BaseModel

class A(BaseModel):
    a:int

def test_something():
    for _ in [1,2]:
        assert A(a=1) == snapshot(A(a=1))
""").run_inline(
        changed_files=snapshot({}),
    )


def test_pydantic_factory_method():
    Example("""\
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
""").run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot({"tests/test_something.py": """\
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
"""}),
    )


@pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="NewType is a function in 3.9 and cannot be checked with isinstance or serialized to code",
)
def test_pydantic_newtype():
    Example("""\
from typing import NewType
from pydantic import BaseModel
from inline_snapshot import snapshot


def test_something():
    SomeID = NewType("SomeID", int)

    class Something(BaseModel):
        some_id: SomeID
    a = Something(some_id=SomeID(1))
    assert a == snapshot()
""").run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot({"tests/test_something.py": """\
from typing import NewType
from pydantic import BaseModel
from inline_snapshot import snapshot


def test_something():
    SomeID = NewType("SomeID", int)

    class Something(BaseModel):
        some_id: SomeID
    a = Something(some_id=SomeID(1))
    assert a == snapshot(Something(some_id=SomeID(1)))
"""}),
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
        changed_files=snapshot({"test_something.py": """\
from inline_snapshot import snapshot
from some_id import create

from some_id import SomeID
from some_id import Something

def test_something():
    assert create() == snapshot(Something(some_id1=SomeID(1)))
"""}),
    ).run_inline()


@pytest.fixture
def generic_model_import():
    if pydantic.version.VERSION.startswith("1."):
        return "from pydantic.generics import GenericModel as BaseModel"
    return "from pydantic import BaseModel"


def test_pydantic_generic_class(generic_model_import):
    Example(f"""\
from typing import Generic, TypeVar
from inline_snapshot import snapshot
{generic_model_import}

I=TypeVar("I")
class C(BaseModel,Generic[I]):
    a:I

def test_a():
    c=C[int](a=5)

    assert c == snapshot()
""").run_inline(
        ["--inline-snapshot=create"],
        changed_files={"tests/test_something.py": Is(f"""\
from typing import Generic, TypeVar
from inline_snapshot import snapshot
{generic_model_import}

I=TypeVar("I")
class C(BaseModel,Generic[I]):
    a:I

def test_a():
    c=C[int](a=5)

    assert c == snapshot(C[int](a=5))
""")},
    ).run_inline()


@pytest.mark.parametrize(
    "parameters, fields, expression, expected",
    [
        ("I", "a: I", "C[int]", "C[int]"),
        ("I", "a: I", "C[C[int]]", "C[C[int]]"),
        ("I", "a: I", "C[C[int]](a=C[int](a=5))", "C[C[int]](a=C[int](a=5))"),
        ("I, J", "a: I\n    b: J", "C[int, str]", "C[int, str]"),
        (
            "I, J",
            "a: I\n    b: J",
            "C[int, str](a=5, b='x')",
            'C[int, str](a=5, b="x")',
        ),
    ],
)
def test_pydantic_generic_type_arguments(
    parameters, fields, expression, expected, generic_model_import
):
    source = f"""\
from typing import Generic, TypeVar
from inline_snapshot import snapshot
{generic_model_import}

I = TypeVar("I")
J = TypeVar("J")

class C(BaseModel, Generic[{parameters}]):
    {fields}

def test_generic():
    for _ in range(2):
        assert {expression} == snapshot()
"""
    Example(source).run_inline(
        ["--inline-snapshot=create"],
        changed_files={
            "tests/test_something.py": Is(
                source.replace("snapshot()", f"snapshot({expected})")
            )
        },
    ).run_inline(changed_files={}).run_inline(
        ["--inline-snapshot=disable"], reported_categories=set()
    )


def test_pydantic_generic_local_alias(generic_model_import):
    source = f"""\
from typing import Generic, TypeVar
from inline_snapshot import snapshot
{generic_model_import}

I = TypeVar("I")

class C(BaseModel, Generic[I]):
    a: I

def test_generic():
    IntC = C[int]
    for _ in range(2):
        assert IntC(a=5) == snapshot()
"""
    Example(source).run_inline(
        ["--inline-snapshot=create"],
        changed_files={
            "tests/test_something.py": Is(
                source.replace("snapshot()", "snapshot(IntC(a=5))")
            )
        },
    ).run_inline(changed_files={}).run_inline(
        ["--inline-snapshot=disable"], reported_categories=set()
    )


def test_pydantic_generic_update_origin(generic_model_import):
    source = f"""\
from typing import Generic, TypeVar
from inline_snapshot import snapshot
{generic_model_import}

I = TypeVar("I")

class C(BaseModel, Generic[I]):
    a: I

def test_generic():
    assert C[int](a=5) == snapshot(C(a=5))
"""
    Example(source).run_inline(
        ["--inline-snapshot=update"],
        changed_files={
            "tests/test_something.py": Is(
                source.replace("snapshot(C(a=5))", "snapshot(C[int](a=5))")
            )
        },
    ).run_inline(changed_files={})


@pytest.mark.parametrize(
    "expression",
    [
        "C[int, J]",
        pytest.param(
            "C[int, J][str]",
            marks=pytest.mark.skipif(
                not pydantic.version.VERSION.startswith("1."),
                reason="v1-specific reconstruction of chained specialization origins",
            ),
        ),
        pytest.param(
            'C[int, J][str](a=5, b="x")',
            marks=pytest.mark.skipif(
                not pydantic.version.VERSION.startswith("1."),
                reason="v1-specific reconstruction of chained specialization origins",
            ),
        ),
    ],
)
def test_pydantic_generic_partial(expression, generic_model_import):
    source = f"""\
from typing import Generic, TypeVar
from inline_snapshot import snapshot
{generic_model_import}

I = TypeVar("I")
J = TypeVar("OtherName")

class C(BaseModel, Generic[I, J]):
    a: I
    b: J

def test_generic():
    for _ in range(2):
        assert {expression} == snapshot()
"""
    Example(source).run_inline(
        ["--inline-snapshot=create"],
        changed_files={
            "tests/test_something.py": Is(
                source.replace("snapshot()", f"snapshot({expression})")
            )
        },
    ).run_inline(changed_files={}).run_inline(
        ["--inline-snapshot=disable"], reported_categories=set()
    )


@pytest.mark.parametrize(
    "declaration, expression",
    [
        ("class Child(C[I], Generic[I]):\n    pass", "Child[int](a=5)"),
        ("class Child(C[int]):\n    pass", "Child(a=5)"),
    ],
)
def test_pydantic_generic_subclass(declaration, expression, generic_model_import):
    source = f"""\
from typing import Generic, TypeVar
from inline_snapshot import snapshot
{generic_model_import}

I = TypeVar("I")

class C(BaseModel, Generic[I]):
    a: I

{declaration}

def test_generic():
    for _ in range(2):
        assert {expression} == snapshot()
"""
    Example(source).run_inline(
        ["--inline-snapshot=create"],
        changed_files={
            "tests/test_something.py": Is(
                source.replace("snapshot()", f"snapshot({expression})")
            )
        },
    ).run_inline(changed_files={}).run_inline(
        ["--inline-snapshot=disable"], reported_categories=set()
    )
