from inline_snapshot._inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


def test_max_hash():
    Example(
        {
            "test_something.py": """\
from inline_snapshot import external
def test_a():
    assert "a" == external()
""",
            "pyproject.toml": """\
[tool.inline-snapshot]
hash-length=64
default-storage="hash"
""",
        }
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                ".inline-snapshot/external/ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb.txt": "a",
                "test_something.py": """\
from inline_snapshot import external
def test_a():
    assert "a" == external("hash:ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb.txt")
""",
            }
        ),
    )
