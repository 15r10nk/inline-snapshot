from inline_snapshot import snapshot
from inline_snapshot.testing import Example


def test_uuid_storage():
    Example(
        """
from inline_snapshot import external

s=external("uuid:")

def test_a():
    assert "value" == external("uuid:")
    assert "blub"==s
    """
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "tests/__inline_snapshot__/test_something/__module__/f728b4fa-4248-4e3a-8a5d-2f346baa9455.txt": "blub",
                "tests/__inline_snapshot__/test_something/test_a/e3e70682-c209-4cac-a29f-6fbed82c07cd.txt": "value",
                "tests/test_something.py": """\

from inline_snapshot import external

s=external("uuid:f728b4fa-4248-4e3a-8a5d-2f346baa9455.txt")

def test_a():
    assert "value" == external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.txt")
    assert "blub"==s
    \
""",
            }
        ),
    ).replace(
        '"value"', '"new_value"'
    ).run_inline(
        ["--inline-snapshot=disable"],
        changed_files=snapshot({}),
        raises=snapshot("AssertionError:\n"),
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "tests/__inline_snapshot__/test_something/test_a/e3e70682-c209-4cac-a29f-6fbed82c07cd.txt": "new_value"
            }
        ),
    ).run_inline(
        ["--inline-snapshot=disable"], changed_files=snapshot({})
    )
