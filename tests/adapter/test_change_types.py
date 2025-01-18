import pytest

from inline_snapshot.testing._example import Example

values = ["1", '"2\'"', "[5]", "{1: 2}", "F(i=5)", "F.make1('2')", "f(7)"]


@pytest.mark.parametrize("a", values)
@pytest.mark.parametrize("b", values + ["F.make2(Is(5))"])
def test_change_types(a, b):
    context = """\
from inline_snapshot import snapshot, Is
from dataclasses import dataclass

@dataclass
class F:
    i: int

    @staticmethod
    def make1(s):
        return F(i=int(s))

    @staticmethod
    def make2(s):
        return F(i=s)

def f(v):
    return v

"""

    def code_repr(v):
        g = {}
        exec(context + f"r=repr({a})", g)
        return g["r"]

    def code(a, b):
        return f"""\
{context}

def test_change():
    for _ in [1,2]:
        assert {a} == snapshot({b})
"""

    print(a, b)
    print(code_repr(a), code_repr(b))

    Example(code(a, b)).run_inline(
        ["--inline-snapshot=fix,update"],
        changed_files=(
            {"test_something.py": code(a, code_repr(a))} if code_repr(a) != b else {}
        ),
    )
