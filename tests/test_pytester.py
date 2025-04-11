from inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


def test_run_pytester():
    Example(
        {
            "conftest.py": """\
pytest_plugins = ["pytester"]
""",
            "test_things.py": """\
from inline_snapshot import snapshot

def test_not_pytester():
    assert "hey" == snapshot()

def test_pytester(pytester):
    pytester.runpytest()
""",
        }
    ).run_pytest(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "test_things.py": """\
from inline_snapshot import snapshot

def test_not_pytester():
    assert "hey" == snapshot("hey")

def test_pytester(pytester):
    pytester.runpytest()
"""
            }
        ),
        returncode=1,
    ).run_pytest(
        ["--inline-snapshot=disable"]
    )
