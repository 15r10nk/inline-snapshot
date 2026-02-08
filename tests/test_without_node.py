import pytest
from executing import is_pytest_compatible

from inline_snapshot.testing import Example


@pytest.mark.skipIf(
    is_pytest_compatible, reason="this is only a problem when executing can return None"
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
