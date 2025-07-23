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


def test_tests_dir():

    Example(
        {
            "pyproject.toml": """\
[tool.inline-snapshot]
test-dir="my_tests"
""",
            "my_tests/test_a.py": """\
from inline_snapshot import external

def test_a():
    assert "a" == external()
    assert "b" == external()
""",
        }
    ).run_pytest(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "my_tests/__inline_snapshot__/test_a/test_a/e3e70682-c209-4cac-a29f-6fbed82c07cd.txt": "a",
                "my_tests/__inline_snapshot__/test_a/test_a/f728b4fa-4248-4e3a-8a5d-2f346baa9455.txt": "b",
                "my_tests/test_a.py": """\
from inline_snapshot import external

def test_a():
    assert "a" == external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.txt")
    assert "b" == external("uuid:f728b4fa-4248-4e3a-8a5d-2f346baa9455.txt")
""",
            }
        ),
        returncode=snapshot(1),
    ).replace(
        "test_a", "test_b"
    ).run_pytest().remove_file(
        "my_tests/__inline_snapshot__/test_a/test_a/f728b4fa-4248-4e3a-8a5d-2f346baa9455.txt"
    ).run_pytest(
        returncode=snapshot(1)
    )


def test_trim():

    Example(
        """\
from inline_snapshot import external

def test_a():
    assert "a" == external()
    assert "b" == external()
"""
    ).run_pytest(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "__inline_snapshot__/test_something/test_a/e3e70682-c209-4cac-a29f-6fbed82c07cd.txt": "a",
                "__inline_snapshot__/test_something/test_a/f728b4fa-4248-4e3a-8a5d-2f346baa9455.txt": "b",
                "test_something.py": """\
from inline_snapshot import external

def test_a():
    assert "a" == external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.txt")
    assert "b" == external("uuid:f728b4fa-4248-4e3a-8a5d-2f346baa9455.txt")
""",
            }
        ),
        returncode=snapshot(1),
    ).replace(
        'assert "b" == external("uuid:f728b4fa-4248-4e3a-8a5d-2f346baa9455.txt")', ""
    ).run_pytest(
        ["--inline-snapshot=trim"],
        changed_files=snapshot(
            {
                "__inline_snapshot__/test_something/test_a/f728b4fa-4248-4e3a-8a5d-2f346baa9455.txt": None
            }
        ),
        returncode=snapshot(0),
    )
