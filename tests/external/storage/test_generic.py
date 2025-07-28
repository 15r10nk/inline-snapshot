import pytest

from inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


@pytest.mark.parametrize("storage", ["uuid", "hash"])
def test_generic(storage):
    Example(
        f"""\
from inline_snapshot import external

def test_a():
    assert "testa".upper()==external("{storage}:")
"""
    ).run_pytest(
        ["--inline-snapshot=report"],
        returncode=snapshot(1),
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "uuid": {
                    "tests/__inline_snapshot__/test_something/test_a/e3e70682-c209-4cac-a29f-6fbed82c07cd.txt": "TESTA",
                    "tests/test_something.py": """\
from inline_snapshot import external

def test_a():
    assert "testa".upper()==external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.txt")
""",
                },
                "hash": {
                    ".inline-snapshot/external/8b95fa6246dc4446718de0b06cbf083677e4b1ec3bace1599d4daf84768f67ee.txt": "TESTA",
                    "tests/test_something.py": """\
from inline_snapshot import external

def test_a():
    assert "testa".upper()==external("hash:8b95fa6246dc*.txt")
""",
                },
            }
        )[storage],
    ).replace(
        "testa", "testb"
    ).run_pytest(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "uuid": {
                    "tests/__inline_snapshot__/test_something/test_a/e3e70682-c209-4cac-a29f-6fbed82c07cd.txt": "TESTB"
                },
                "hash": {
                    ".inline-snapshot/external/78e8a8fafad325dcf5ba036e127b88ed56131b8daaf6fcd925722bc3dccead72.txt": "TESTB",
                    "tests/test_something.py": """\
from inline_snapshot import external

def test_a():
    assert "testb".upper()==external("hash:78e8a8fafad3*.txt")
""",
                },
            }
        )[storage],
        report=snapshot(
            {
                "uuid": """\
+--------------- uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.txt ----------------+
| @@ -1 +1 @@                                                                  |
|                                                                              |
| -TESTA                                                                       |
| +TESTB                                                                       |
+------------------------------------------------------------------------------+
These changes will be applied, because you used fix\
""",
                "hash": """\
-------------------------------- Fix snapshots ---------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -1,4 +1,4 @@                                                              |
|                                                                              |
|  from inline_snapshot import external                                        |
|                                                                              |
|  def test_a():                                                               |
| -    assert "testb".upper()==external("hash:8b95fa6246dc*.txt")              |
| +    assert "testb".upper()==external("hash:78e8a8fafad3*.txt")              |
+------------------------------------------------------------------------------+
+-------------- hash:8b95fa6246dc*.txt -> hash:78e8a8fafad3*.txt --------------+
| @@ -1 +1 @@                                                                  |
|                                                                              |
| -TESTA                                                                       |
| +TESTB                                                                       |
+------------------------------------------------------------------------------+
These changes will be applied, because you used fix\
""",
            }
        )[storage],
        returncode=1,
    )
