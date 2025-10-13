import ast
import sys

from inline_snapshot import external
from inline_snapshot import outsource
from inline_snapshot import snapshot
from inline_snapshot._external._find_external import ensure_import
from inline_snapshot._external._find_external import used_externals_in
from inline_snapshot._global_state import snapshot_env
from inline_snapshot.extra import raises
from inline_snapshot.testing import Example

from ..utils import apply_changes


def test_basic(check_update):
    assert check_update(
        "assert outsource('text') == snapshot()", flags="create"
    ) == snapshot(
        "assert outsource('text') == snapshot(external(\"hash:982d9e3eb996*.txt\"))"
    )


# def test_external():
#     assert repr(external("11111111112222222222.txt")) == snapshot(
#         'external("111111111122*.txt")'
#     )


def test_outsource():

    Example(
        """\
from inline_snapshot import outsource, snapshot,external,register_format_alias

register_format_alias(".log",".txt")

def test_a():
    assert outsource("test") == external()

    assert outsource("test", suffix=".log") == external()

    assert outsource(b"test") == external()
"""
    ).run_pytest(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                ".inline-snapshot/external/9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08.bin": "test",
                ".inline-snapshot/external/9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08.log": "test",
                ".inline-snapshot/external/9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08.txt": "test",
                "tests/__inline_snapshot__/test_something/test_a/e3e70682-c209-4cac-a29f-6fbed82c07cd.txt": "test",
                "tests/__inline_snapshot__/test_something/test_a/eb1167b3-67a9-4378-bc65-c1e582e2e662.bin": "test",
                "tests/__inline_snapshot__/test_something/test_a/f728b4fa-4248-4e3a-8a5d-2f346baa9455.log": "test",
                "tests/test_something.py": """\
from inline_snapshot import outsource, snapshot,external,register_format_alias

register_format_alias(".log",".txt")

def test_a():
    assert outsource("test") == external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.txt")

    assert outsource("test", suffix=".log") == external("uuid:f728b4fa-4248-4e3a-8a5d-2f346baa9455.log")

    assert outsource(b"test") == external("uuid:eb1167b3-67a9-4378-bc65-c1e582e2e662.bin")
""",
            }
        ),
        returncode=1,
    ).run_pytest(
        ["--inline-snapshot=disable"]
    )


def test_diskstorage():
    with snapshot_env():

        assert outsource("test4") == snapshot(external("hash:a4e624d686e0*.txt"))
        assert outsource("test5") == snapshot(external("hash:a140c0c1eda2*.txt"))
        assert outsource("test6") == snapshot(external("hash:ed0cb90bdfa4*.txt"))

        with raises(
            snapshot(
                "StorageLookupError: hash collision files=['a140c0c1eda2def2b830363ba362aa4d7d255c262960544821f556e16661b6ff.txt', 'a4e624d686e03ed2767c0abd85c14426b0b1157d2ce81d27bb4fe4f6f01d688a.txt']"
            )
        ):
            assert outsource("test4") == external("hash:a*.txt")

        with raises(
            snapshot(
                "StorageLookupError: hash 'bbbbb*.txt' is not found in the HashStorage"
            )
        ):
            assert outsource("test4") == external("hash:bbbbb*.txt")


def test_update_legacy_external_names(project):
    (
        Example(
            """\
from inline_snapshot import outsource,snapshot

def test_something():
    assert outsource("foo") == snapshot()
"""
        )
        .run_pytest(
            ["--inline-snapshot=create"],
            changed_files=snapshot(
                {
                    ".inline-snapshot/external/2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae.txt": "foo",
                    "tests/test_something.py": """\
from inline_snapshot import outsource,snapshot

from inline_snapshot import external

def test_something():
    assert outsource("foo") == snapshot(external("hash:2c26b46b68ff*.txt"))
""",
                }
            ),
            returncode=1,
        )
        .run_inline(reported_categories=snapshot([]))
        .change_code(lambda code: code.replace("hash:", ""))
        .run_inline(reported_categories=snapshot(["update"]))
        .run_inline(
            ["--inline-snapshot=update"],
            reported_categories=snapshot(["update"]),
            changed_files=snapshot(
                {
                    "tests/test_something.py": """\
from inline_snapshot import outsource,snapshot

from inline_snapshot import external

def test_something():
    assert outsource("foo") == snapshot(external("hash:2c26b46b68ff*.txt"))
"""
                }
            ),
        )
    )


def test_pytest_compare_external(project):
    project.setup(
        """\
from inline_snapshot import external

def test_a():
    s=snapshot()
    assert outsource("test") == s

    assert outsource("test2") == s
        """
    )
    result = project.run("--inline-snapshot=create")

    result = project.run()

    assert result.errorLines() == snapshot(
        """\
>       assert outsource("test2") == s
E       AssertionError: assert 'test2' == 'test'
E         \n\
E         - test
E         + test2
E         ?     +
"""
    )


def test_pytest_compare_external_bytes(project):
    project.setup(
        """\
from inline_snapshot import external

def test_a():
    assert outsource(b"test") == snapshot(
        external("hash:9f86d081884c*.bin")
    )

    assert outsource(b"test2") == snapshot(
        external("hash:9f86d081884c*.bin")
    )
        """
    )

    result = project.run("--inline-snapshot=create")

    assert result.errorLines() == (
        snapshot(
            """\
>       assert outsource(b"test2") == snapshot(
E       AssertionError: assert b'test2' == b'test'
E         \n\
E         Use -v to get more diff
"""
        )
        if sys.version_info >= (3, 11)
        else snapshot(
            """\
>       assert outsource(b"test2") == snapshot(
E       AssertionError
"""
        )
    )


def test_pytest_existing_external_import(project):
    project.setup(
        """\
from inline_snapshot import external

def test_a():
    assert outsource("test") == snapshot()
"""
    )

    project.run("--inline-snapshot=create")

    assert project.source == snapshot(
        """\
from inline_snapshot import external

def test_a():
    assert outsource("test") == snapshot(external("hash:9f86d081884c*.txt"))
"""
    )


def test_pytest_trim_external(project):
    project.setup(
        """\
def test_a():
    assert outsource("test") == snapshot()

    # split

    assert outsource("test2") == snapshot()
        """
    )

    project.run("--inline-snapshot=create")

    assert project.storage() == snapshot(
        [
            "60303ae22b998861bce3b28f33eec1be758a213c86c93c076dbe9f558c11c752.txt",
            "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08.txt",
        ]
    )

    assert project.source == snapshot(
        """\
from inline_snapshot import external


def test_a():
    assert outsource("test") == snapshot(external("hash:9f86d081884c*.txt"))

    # split

    assert outsource("test2") == snapshot(external("hash:60303ae22b99*.txt"))
        \
"""
    )

    project.setup(project.source.split("# split")[0])
    result = project.run()

    assert project.storage() == snapshot(
        [
            "60303ae22b998861bce3b28f33eec1be758a213c86c93c076dbe9f558c11c752.txt",
            "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08.txt",
        ]
    )

    assert result.report == snapshot("")

    result = project.run("--inline-snapshot=trim")

    assert project.storage() == snapshot(
        ["9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08.txt"]
    )


def test_pytest_new_external(project):
    project.setup(
        """\
def test_a():
    assert outsource("test") == snapshot()
"""
    )
    project.run()

    assert project.storage() == snapshot(
        ["9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08.txt"]
    )

    project.run("--inline-snapshot=create")

    assert project.storage() == snapshot(
        ["9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08.txt"]
    )


def test_pytest_config_hash_length(project):
    project.setup(
        """\
def test_a():
    assert outsource("test") == snapshot()
"""
    )
    project.run("--inline-snapshot=create")
    default_result = project.source

    # default config
    project.pyproject(
        """
[tool.inline-snapshot]
    """
    )
    project.run("--inline-snapshot=create")
    assert default_result == project.source

    # set hash_length
    project.pyproject(
        """
[tool.inline-snapshot]
hash-length=5
    """
    )
    project.run("--inline-snapshot=create")
    assert project.source == snapshot(
        """\
from inline_snapshot import external


def test_a():
    assert outsource("test") == snapshot(external("hash:9f86d081884c*.txt"))
"""
    )


def test_errors():
    with raises(snapshot("ValueError: suffix has to start with a '.' like '.png'")):
        with snapshot_env():
            outsource("test", suffix="blub")

    with raises(
        snapshot(
            "UsageError: No format handler found for the given type 'test_errors.<locals>.C'."
        )
    ):

        class C: ...

        with snapshot_env():
            outsource(C())

    with raises(snapshot("ValueError: 'invalid' is missing a suffix")):
        with snapshot_env():
            external("invalid")


def test_uses_external():
    assert used_externals_in(
        ast.parse("[external('hash:111*.txt')]"), check_import=False
    ) == snapshot({"hash:111*.txt"})
    assert not used_externals_in(ast.parse("[external()]"), check_import=False)
    assert not used_externals_in(ast.parse("[external]"), check_import=False)
    assert used_externals_in(
        ast.parse("[external('hash:111*.txt')]"), check_import=True
    ) == snapshot(set())


def test_no_imports(project):
    project.setup(
        """\
# no imports

def test_something():
    from inline_snapshot import outsource,snapshot
    assert outsource("test") == snapshot()
test_something()
    """
    )

    result = project.run("--inline-snapshot=create")

    result.assert_outcomes(errors=1, passed=1)

    assert project.source == snapshot(
        """\
# no imports


from inline_snapshot import external
def test_something():
    from inline_snapshot import outsource,snapshot
    assert outsource("test") == snapshot(external("hash:9f86d081884c*.txt"))
test_something()
    \
"""
    )


def test_ensure_imports(tmp_path):
    file = tmp_path / "file.py"
    file.write_bytes(
        b"""\
from os import environ
from os import getcwd
"""
    )

    with apply_changes() as recorder:
        ensure_import(file, {"os": ["chdir", "environ"]}, recorder)

    assert file.read_text("utf-8") == snapshot(
        """\
from os import environ
from os import getcwd

from os import chdir
"""
    )


def test_ensure_imports_with_comment(tmp_path):
    file = tmp_path / "file.py"
    file.write_bytes(
        b"""\
from os import environ # comment
"""
    )

    with apply_changes() as recorder:
        ensure_import(file, {"os": ["chdir"]}, recorder)

    assert file.read_text("utf-8") == snapshot(
        """\
from os import environ # comment

from os import chdir
"""
    )


def test_new_externals(project):
    project.setup(
        """

def test_something():
    outsource("blub")

    assert outsource("foo") == snapshot()

    """
    )

    project.run("--inline-snapshot=create")

    assert project.storage() == snapshot(
        [
            "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae.txt",
            "8dc140e6fe831481a2005ae152ffe32a9974aa92a260dfbac780d6a87154bb0b.txt",
        ]
    )

    assert project.source == snapshot(
        """\
from inline_snapshot import external




def test_something():
    outsource("blub")

    assert outsource("foo") == snapshot(external("hash:2c26b46b68ff*.txt"))

    \
"""
    )

    project.run()

    assert project.storage() == snapshot(
        [
            "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae.txt",
            "8dc140e6fe831481a2005ae152ffe32a9974aa92a260dfbac780d6a87154bb0b.txt",
        ]
    )


def test_persist_twice():
    Example(
        """\
from inline_snapshot import snapshot,outsource

def test_a():
    assert outsource("testabc") == snapshot()
    assert 1+1==snapshot()
"""
    ).run_pytest(["--inline-snapshot=create"], returncode=1).change_code(
        lambda text: text.replace("snapshot(2)", "snapshot()")
    ).run_pytest(
        ["--inline-snapshot=create"], returncode=1
    )


def test_disable():
    Example(
        """
from inline_snapshot import external, snapshot,outsource

def test_something():
    assert outsource("foo") == snapshot()
    assert "foo" == external()
"""
    ).run_pytest(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                ".inline-snapshot/external/2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae.txt": "foo",
                "tests/__inline_snapshot__/test_something/test_something/e3e70682-c209-4cac-a29f-6fbed82c07cd.txt": "foo",
                "tests/test_something.py": """\

from inline_snapshot import external, snapshot,outsource

def test_something():
    assert outsource("foo") == snapshot(external("hash:2c26b46b68ff*.txt"))
    assert "foo" == external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.txt")
""",
            }
        ),
        returncode=1,
    ).run_pytest(
        ["--inline-snapshot=disable"]
    )

    Example(
        """
from inline_snapshot import external

def test_something():
    assert "foo" == external("hash:aaaaaaaaaaaa*.txt")
"""
    ).run_pytest(
        ["--inline-snapshot=disable"],
        error=snapshot(
            """\
>       assert "foo" == external("hash:aaaaaaaaaaaa*.txt")
>           raise StorageLookupError(f"hash {name!r} is not found in the HashStorage")
E           inline_snapshot._external._storage._protocol.StorageLookupError: hash 'aaaaaaaaaaaa*.txt' is not found in the HashStorage
"""
        ),
        returncode=1,
    )


def test_show_diff():
    Example(
        """
from inline_snapshot import external

def test_a():
    n=3
    assert "\\n".join(map(str,range(n))) == external()
    """
    ).run_pytest(
        ["--inline-snapshot=create"],
        report=snapshot(
            """\
------------------------------- Create snapshots -------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -3,5 +3,5 @@                                                              |
|                                                                              |
|                                                                              |
|  def test_a():                                                               |
|      n=3                                                                     |
| -    assert "\\n".join(map(str,range(n))) == external()                       |
| +    assert "\\n".join(map(str,range(n))) ==                                  |
| external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.txt")                    |
+------------------------------------------------------------------------------+
+--------------- uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.txt ----------------+
| 0                                                                            |
| 1                                                                            |
| 2                                                                            |
+------------------------------------------------------------------------------+
These changes will be applied, because you used create\
"""
        ),
        returncode=1,
    ).change_code(
        lambda text: text.replace("n=3", "n=5")
    ).run_pytest(
        ["--inline-snapshot=fix"],
        report=snapshot(
            """\
+--------------- uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.txt ----------------+
| @@ -1,3 +1,5 @@                                                              |
|                                                                              |
|  0                                                                           |
|  1                                                                           |
|  2                                                                           |
| +3                                                                           |
| +4                                                                           |
+------------------------------------------------------------------------------+
These changes will be applied, because you used fix\
"""
        ),
        returncode=1,
    )


def test_double_eq():
    Example(
        """
from inline_snapshot import external

def test_a():
    assert "hi" == external(".json") == external(".txt")
    """
    ).run_pytest(
        ["--inline-snapshot=create"],
        error=snapshot(
            """\
>       assert "hi" == external(".json") == external(".txt")
E       inline_snapshot._exceptions.UsageError: you can not compare external(...) with external(...)
"""
        ),
        returncode=1,
    )


def test_external_eq_snapshot():
    Example(
        """
from inline_snapshot import external, snapshot

def test_a():
    assert "hi" == external(".json") == snapshot(".txt")
    """
    ).run_pytest(
        ["--inline-snapshot=create"],
        error=snapshot(
            """\
>       assert "hi" == external(".json") == snapshot(".txt")
E       inline_snapshot._exceptions.UsageError: you can not compare external(...) with snapshot(...)
"""
        ),
        returncode=1,
    )


def test_unknown_suffix():
    Example(
        """
from inline_snapshot import external

def test_a():
    assert "hi" == external("uuid:.blub")
    """
    ).run_pytest(
        ["--inline-snapshot=create"],
        error=snapshot(
            """\
>       assert "hi" == external("uuid:.blub")
>           raise UsageError(
E           inline_snapshot._exceptions.UsageError: No format handler found for the given type 'str' and suffix '.blub'.
"""
        ),
        returncode=1,
    )


def test_unknown_type():
    Example(
        """
from inline_snapshot import external

class C:...

def test_a():
    assert C() == external("uuid:")
    """
    ).run_pytest(
        ["--inline-snapshot=create"],
        error=snapshot(
            """\
>       assert C() == external("uuid:")
>           raise UsageError(
E           inline_snapshot._exceptions.UsageError: No format handler found for the given type 'C'.
"""
        ),
        returncode=1,
    )


def test_missing():

    Example(
        """
from inline_snapshot import external

def test_a():
    n=3
    assert "hi" == external()
    """
    ).run_pytest(
        ["--inline-snapshot=short-report"],
        error=snapshot(
            """\
>       assert "hi" == external()
E       assert 'hi' == external("uuid:")
E        +  where external("uuid:") = external()
"""
        ),
        report=snapshot(
            """\
Error: one snapshot is missing a value (--inline-snapshot=create)
You can also use --inline-snapshot=review to approve the changes interactively\
"""
        ),
        returncode=1,
    ).run_pytest(
        ["--inline-snapshot=disable"],
        error=snapshot(
            """\
>       assert "hi" == external()
>           raise UsageError(
E           inline_snapshot._exceptions.UsageError: can not load external object from an non existing location 'uuid:'
"""
        ),
        report=snapshot(""),
        returncode=1,
    )


def test_tests_dir():
    Example(
        {
            "pyproject.toml": "# empty",
            "example1.py": """\
from inline_snapshot import external

def test_a():
    assert "hi" == external("hash:")
""",
            "tests/example2.py": """\
from inline_snapshot import external

def test_a():
    assert "ho" == external("hash:")
""",
        }
    ).run_pytest(
        ["--inline-snapshot=create", "example1.py", "tests/example2.py"],
        changed_files=snapshot(
            {
                ".inline-snapshot/external/8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4.txt": "hi",
                ".inline-snapshot/external/a821c62e8104f8519d639b4c0948aece641b143f6601fa145993bb2e2c7299d4.txt": "ho",
                "example1.py": """\
from inline_snapshot import external

def test_a():
    assert "hi" == external("hash:8f434346648f*.txt")
""",
                "tests/example2.py": """\
from inline_snapshot import external

def test_a():
    assert "ho" == external("hash:a821c62e8104*.txt")
""",
            }
        ),
        returncode=snapshot(1),
    ).run_pytest(
        ["--inline-snapshot=trim", "example1.py"],
        changed_files=snapshot({}),
        returncode=snapshot(0),
    ).run_pytest(
        ["--inline-snapshot=trim", "tests/example2.py"],
        changed_files=snapshot(
            {
                ".inline-snapshot/external/8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4.txt": None
            }
        ),
        returncode=snapshot(0),
    )


def test_report():
    # see https://github.com/15r10nk/inline-snapshot/issues/298

    Example(
        """\

from inline_snapshot import external


def test_example():
    n=5
    assert sorted([n, 2]) == external()


"""
    ).run_pytest(
        ["--inline-snapshot=report"],
        report=snapshot(
            """\
------------------------------- Create snapshots -------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -4,6 +4,6 @@                                                              |
|                                                                              |
|                                                                              |
|  def test_example():                                                         |
|      n=5                                                                     |
| -    assert sorted([n, 2]) == external()                                     |
| +    assert sorted([n, 2]) ==                                                |
| external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.json")                   |
+------------------------------------------------------------------------------+
+--------------- uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.json ---------------+
| [                                                                            |
|   2,                                                                         |
|   5                                                                          |
| ]                                                                            |
+------------------------------------------------------------------------------+
These changes are not applied.
Use --inline-snapshot=create to apply them, or use the interactive mode with
--inline-snapshot=review\
"""
        ),
        returncode=snapshot(1),
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "tests/__inline_snapshot__/test_something/test_example/e3e70682-c209-4cac-a29f-6fbed82c07cd.json": """\
[
  2,
  5
]\
""",
                "tests/test_something.py": """\

from inline_snapshot import external


def test_example():
    n=5
    assert sorted([n, 2]) == external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.json")


""",
            }
        ),
    ).replace(
        "n=5", "n=8"
    ).run_pytest(
        ["--inline-snapshot=report"],
        report=snapshot(
            """\
+--------------- uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.json ---------------+
| @@ -1,4 +1,4 @@                                                              |
|                                                                              |
|  [                                                                           |
|    2,                                                                        |
| -  5                                                                         |
| +  8                                                                         |
|  ]                                                                           |
+------------------------------------------------------------------------------+
These changes are not applied.
Use --inline-snapshot=fix to apply them, or use the interactive mode with
--inline-snapshot=review\
"""
        ),
        returncode=snapshot(1),
    )
