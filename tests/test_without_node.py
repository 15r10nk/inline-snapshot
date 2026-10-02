import pytest
from executing import is_pytest_compatible

from inline_snapshot import snapshot
from inline_snapshot.testing import Example


@pytest.mark.skipif(
    is_pytest_compatible(),
    reason="this is only a problem when executing can return None",
)
def test_without_node():

    Example(
        {
            "conftest.py": """\
from inline_snapshot.plugin import customize

@customize
def handler(value,builder):
    if value=="foo":
        return builder.create_code("'foo'")
""",
            "test_example.py": """\
from inline_snapshot import snapshot
from dirty_equals import IsStr

def test_foo():
    assert "not_foo" == snapshot(IsStr())
""",
        }
    ).run_pytest()


def test_custom_default_case_in_ValueToCustom(executing_used):
    Example("""\
from inline_snapshot import snapshot
from dataclasses import dataclass

@dataclass
class A:
    a:int=5

def test_something():
    assert A(a=3) == snapshot(A(a=5)),"not equal"
""").run_inline(
        changed_files=snapshot({}),
        raises=snapshot("AssertionError: not equal"),
        reported_categories={"fix"},
    )


def test_tuple_case_in_ValueToCustom(executing_used):
    Example("""\
from inline_snapshot import snapshot
from dataclasses import dataclass

@dataclass
class A:
    a:int=5

def test_something():
    assert (1,2) == snapshot((1,2)),"not equal"
""").run_inline(
        changed_files=snapshot({}),
        raises=snapshot("<no exception>"),
    )


@pytest.mark.parametrize("value", ["[1]", "(1,)", "{1}", "{'a': [1]}", "A(value=[1])"])
def test_repeated_nested_dataclass(executing_used, value):
    Example(f"""\
from inline_snapshot import snapshot
from dataclasses import dataclass

@dataclass
class A:
    value: object

def test_something():
    for _ in range(2):
        assert snapshot(A(value={value})) == A(value={value})
""").run_inline(reported_categories=set())


@pytest.mark.parametrize("executing_used", [False], indirect=True)
@pytest.mark.parametrize(
    "call",
    [
        "builder.create_call(complex, [builder.create_code(repr(value.real)), value.imag])",
        "builder.create_call(complex, [], {'real': builder.create_code(repr(value.real)), 'imag': value.imag})",
        "builder.create_call(builder.create_code('complex'), [value.real, value.imag])",
    ],
)
def test_explicit_builder_nodes_without_node(executing_used, call):
    Example(
        {
            "conftest.py": f"""\
from inline_snapshot.plugin import customize

@customize
def custom(value, builder):
    if isinstance(value, complex):
        return {call}
""",
            "test_example.py": """\
from inline_snapshot import snapshot

def test_it():
    for _ in range(2):
        assert snapshot(1 + 2j) == 1 + 2j
""",
        }
    ).run_inline(reported_categories=set(), changed_files={})
