from inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


def test_move_files():
    Example(
        {
            "tests/test_move.py": """
import shutil

def test_move():
    from tests.a.test_fa import f

    shutil.copytree("tests/a","tests/b")

    from tests.b.test_fa import f

    f()
""",
            "tests/a/test_fa.py": """
from inline_snapshot import external
def f():
    assert "test" == external()
""",
        }
    ).run_pytest(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "tests/a/__inline_snapshot__/test_fa/f/e3e70682-c209-4cac-a29f-6fbed82c07cd.txt": "test",
                "tests/a/test_fa.py": """\

from inline_snapshot import external
def f():
    assert "test" == external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.txt")
""",
                "tests/b/test_fa.py": """\

from inline_snapshot import external
def f():
    assert "test" == external()
""",
            }
        ),
        returncode=snapshot(1),
    ).run_pytest(
        ["--inline-snapshot=disable"], returncode=snapshot(2)
    )
