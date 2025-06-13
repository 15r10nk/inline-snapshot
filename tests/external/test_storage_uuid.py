from inline_snapshot._inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


def test_uuid_rename_function():

    Example(
        """
from inline_snapshot import external

def test_a():
    assert "a" == external()

"""
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "__inline_snapshot__/test_something/test_a/e3e70682-c209-4cac-a29f-6fbed82c07cd.txt": "a",
                "test_something.py": """\

from inline_snapshot import external

def test_a():
    assert "a" == external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.txt")

""",
            }
        ),
    ).replace(
        "test_a", "test_b"
    ).run_inline()
