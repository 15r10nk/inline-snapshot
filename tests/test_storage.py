from inline_snapshot import snapshot
from inline_snapshot.testing import Example


def test_uuid_storage():
    Example(
        """
from inline_snapshot import external

def test_a():
    assert "value" == external("uuid:")
    """
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "__inline_snapshot__/test_something/test_a/e3e70682-c209-4cac-a29f-6fbed82c07cd.txt": "value",
                "test_something.py": """\

from inline_snapshot import external

def test_a():
    assert "value" == external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.txt")
    \
""",
            }
        ),
    )
