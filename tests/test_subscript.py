from inline_snapshot import snapshot
from inline_snapshot.testing import Example


def test_subscript_update_preserves_structure():
    """Test that updating a subscript preserves the subscript structure."""

    Example(
        {
            "conftest.py": """\
from inline_snapshot.plugin import customize

@customize
def handler(value,global_vars,builder):
    for k,v in global_vars.items():
        if isinstance(v,list):
            for i,e in enumerate(v):
                if e == value:
                    return builder.create_subscript(builder.create_code(k),i)
""",
            "tests/test_something.py": """\
from inline_snapshot import snapshot

data = ["a", "b", "c"]

def test_update():
    # Value stays the same, code might need formatting update
    assert snapshot(data[1]) == "a"
    assert snapshot(data[1]) == "b"
    assert snapshot(data[1]) == "c"
    assert snapshot(data[1]) == "d"
""",
        }
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot({"tests/test_something.py": """\
from inline_snapshot import snapshot

data = ["a", "b", "c"]

def test_update():
    # Value stays the same, code might need formatting update
    assert snapshot(data[0]) == "a"
    assert snapshot(data[1]) == "b"
    assert snapshot(data[2]) == "c"
    assert snapshot("d") == "d"
"""}),
    )
