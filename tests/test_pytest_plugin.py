from pathlib import Path

import pytest
from dirty_equals import IsIgnoreDict
from executing import is_pytest_compatible

from inline_snapshot import snapshot
from inline_snapshot.testing import Example


def test_help_message(testdir):
    result = testdir.runpytest_subprocess("--help")
    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(["inline-snapshot:", "*--inline-snapshot*"])


def test_create():
    Example(
        """\
from inline_snapshot import snapshot

def test_a():
    assert 5==snapshot()
"""
    ).run_pytest(
        ["--inline-snapshot=short-report"],
        outcomes=snapshot({"errors": 1, "passed": 1}),
        report=snapshot(
            """\
Error: one snapshot is missing a value (--inline-snapshot=create)
You can also use --inline-snapshot=review to approve the changes interactively\
"""
        ),
        returncode=1,
    ).run_pytest(
        ["--inline-snapshot=create"],
        outcomes=snapshot({"passed": 1, "errors": 1}),
        report=snapshot(
            """\
------------------------------- Create snapshots -------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -1,4 +1,4 @@                                                              |
|                                                                              |
|  from inline_snapshot import snapshot                                        |
|                                                                              |
|  def test_a():                                                               |
| -    assert 5==snapshot()                                                    |
| +    assert 5==snapshot(5)                                                   |
+------------------------------------------------------------------------------+
These changes will be applied, because you used create\
"""
        ),
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_a():
    assert 5==snapshot(5)
"""
            }
        ),
        returncode=1,
    )


def test_fix():
    Example(
        """\
from inline_snapshot import snapshot

def test_a():
    assert 5==snapshot(4)
"""
    ).run_pytest(
        ["--inline-snapshot=short-report"],
        outcomes=snapshot({"failed": 1, "errors": 1}),
        report=snapshot(
            """\
Error: one snapshot has incorrect values (--inline-snapshot=fix)
You can also use --inline-snapshot=review to approve the changes interactively\
"""
        ),
        returncode=1,
    ).run_pytest(
        ["--inline-snapshot=fix"],
        outcomes=snapshot({"passed": 1, "errors": 1}),
        report=snapshot(
            """\
-------------------------------- Fix snapshots ---------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -1,4 +1,4 @@                                                              |
|                                                                              |
|  from inline_snapshot import snapshot                                        |
|                                                                              |
|  def test_a():                                                               |
| -    assert 5==snapshot(4)                                                   |
| +    assert 5==snapshot(5)                                                   |
+------------------------------------------------------------------------------+
These changes will be applied, because you used fix\
"""
        ),
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_a():
    assert 5==snapshot(5)
"""
            }
        ),
        returncode=1,
    )


def test_update():
    Example(
        """\
from inline_snapshot import snapshot

def test_a():
    assert "5" == snapshot('''5''')
"""
    ).run_pytest(
        ["--inline-snapshot=short-report"],
        outcomes=snapshot({"passed": 1}),
        report=(
            snapshot(
                """\
Info: one snapshot changed its representation (--inline-snapshot=update)
You can also use --inline-snapshot=review to approve the changes interactively\
"""
            )
            if is_pytest_compatible()
            else snapshot("")
        ),
    ).run_pytest(
        ["--inline-snapshot=update"],
        report=snapshot(
            """\
------------------------------- Update snapshots -------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -1,4 +1,4 @@                                                              |
|                                                                              |
|  from inline_snapshot import snapshot                                        |
|                                                                              |
|  def test_a():                                                               |
| -    assert "5" == snapshot('''5''')                                         |
| +    assert "5" == snapshot("5")                                             |
+------------------------------------------------------------------------------+
These changes will be applied, because you used update\
"""
        ),
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_a():
    assert "5" == snapshot("5")
"""
            }
        ),
    )


def test_trim():
    Example(
        """\
from inline_snapshot import snapshot

def test_a():
    assert 5 in snapshot([4,5])
"""
    ).run_pytest(
        ["--inline-snapshot=short-report"],
        outcomes=snapshot({"passed": 1}),
        report=snapshot(
            """\
Info: one snapshot can be trimmed (--inline-snapshot=trim)
You can also use --inline-snapshot=review to approve the changes interactively\
"""
        ),
    ).run_pytest(
        ["--inline-snapshot=trim"],
        report=snapshot(
            """\
-------------------------------- Trim snapshots --------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -1,4 +1,4 @@                                                              |
|                                                                              |
|  from inline_snapshot import snapshot                                        |
|                                                                              |
|  def test_a():                                                               |
| -    assert 5 in snapshot([4,5])                                             |
| +    assert 5 in snapshot([5])                                               |
+------------------------------------------------------------------------------+
These changes will be applied, because you used trim\
"""
        ),
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_a():
    assert 5 in snapshot([5])
"""
            }
        ),
    )


def test_multiple():
    Example(
        """\
from inline_snapshot import snapshot

def test_a():
    assert "5" == snapshot('''5''')
    assert 5 <= snapshot(8)
    assert 5 == snapshot(4)
"""
    ).run_pytest(
        ["--inline-snapshot=short-report"],
        outcomes=snapshot({"failed": 1, "errors": 1}),
        report=(
            snapshot(
                """\
Error: one snapshot has incorrect values (--inline-snapshot=fix)
Info: one snapshot can be trimmed (--inline-snapshot=trim)
Info: one snapshot changed its representation (--inline-snapshot=update)
You can also use --inline-snapshot=review to approve the changes interactively\
"""
            )
            if is_pytest_compatible()
            else snapshot(
                """\
Error: one snapshot has incorrect values (--inline-snapshot=fix)
Info: one snapshot can be trimmed (--inline-snapshot=trim)
You can also use --inline-snapshot=review to approve the changes interactively\
"""
            )
        ),
        returncode=1,
    ).run_pytest(
        ["--inline-snapshot=trim,fix"],
        outcomes=snapshot({"passed": 1, "errors": 1}),
        report=snapshot(
            """\
-------------------------------- Fix snapshots ---------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -3,4 +3,4 @@                                                              |
|                                                                              |
|  def test_a():                                                               |
|      assert "5" == snapshot('''5''')                                         |
|      assert 5 <= snapshot(8)                                                 |
| -    assert 5 == snapshot(4)                                                 |
| +    assert 5 == snapshot(5)                                                 |
+------------------------------------------------------------------------------+
These changes will be applied, because you used fix
-------------------------------- Trim snapshots --------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -2,5 +2,5 @@                                                              |
|                                                                              |
|                                                                              |
|  def test_a():                                                               |
|      assert "5" == snapshot('''5''')                                         |
| -    assert 5 <= snapshot(8)                                                 |
| +    assert 5 <= snapshot(5)                                                 |
|      assert 5 == snapshot(5)                                                 |
+------------------------------------------------------------------------------+
These changes will be applied, because you used trim\
"""
        ),
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_a():
    assert "5" == snapshot('''5''')
    assert 5 <= snapshot(5)
    assert 5 == snapshot(5)
"""
            }
        ),
        returncode=1,
    )


@pytest.mark.no_rewriting
def test_disable_option():
    e = Example(
        """\
from inline_snapshot import snapshot

def test_a():
    pass
"""
    )

    e.run_pytest(
        ["--inline-snapshot=disable,fix"],
        stderr=snapshot(
            "ERROR: --inline-snapshot=disable cannot be combined with other flags (fix)\n"
        ),
        returncode=4,
    )

    e.run_pytest(
        ["--inline-snapshot=disable,review"],
        stderr=snapshot(
            "ERROR: --inline-snapshot=disable cannot be combined with other flags (review)\n"
        ),
        returncode=4,
    )


def test_multiple_report():
    Example(
        {
            "pyproject.toml": """\
[tool.inline-snapshot]
show-updates=true
""",
            "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_a():
    assert "5" == snapshot('''5''')
    assert 5 <= snapshot(8)
    assert 5 == snapshot(4)
""",
        }
    ).run_pytest(
        ["--inline-snapshot=trim,report"],
        outcomes=snapshot({"failed": 1, "errors": 1}),
        report=snapshot(
            """\
-------------------------------- Fix snapshots ---------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -3,4 +3,4 @@                                                              |
|                                                                              |
|  def test_a():                                                               |
|      assert "5" == snapshot('''5''')                                         |
|      assert 5 <= snapshot(8)                                                 |
| -    assert 5 == snapshot(4)                                                 |
| +    assert 5 == snapshot(5)                                                 |
+------------------------------------------------------------------------------+
These changes are not applied.
Use --inline-snapshot=fix to apply them, or use the interactive mode with
--inline-snapshot=review
-------------------------------- Trim snapshots --------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -2,5 +2,5 @@                                                              |
|                                                                              |
|                                                                              |
|  def test_a():                                                               |
|      assert "5" == snapshot('''5''')                                         |
| -    assert 5 <= snapshot(8)                                                 |
| +    assert 5 <= snapshot(5)                                                 |
|      assert 5 == snapshot(4)                                                 |
+------------------------------------------------------------------------------+
These changes will be applied, because you used trim
------------------------------- Update snapshots -------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -1,6 +1,6 @@                                                              |
|                                                                              |
|  from inline_snapshot import snapshot                                        |
|                                                                              |
|  def test_a():                                                               |
| -    assert "5" == snapshot('''5''')                                         |
| +    assert "5" == snapshot("5")                                             |
|      assert 5 <= snapshot(5)                                                 |
|      assert 5 == snapshot(4)                                                 |
+------------------------------------------------------------------------------+
These changes are not applied.
Use --inline-snapshot=update to apply them, or use the interactive mode with
--inline-snapshot=review\
"""
        ),
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_a():
    assert "5" == snapshot('''5''')
    assert 5 <= snapshot(5)
    assert 5 == snapshot(4)
"""
            }
        ),
        returncode=1,
    )


def test_black_config():
    e = Example(
        """\
from inline_snapshot import snapshot

def test_a():
    assert list(range(10)) == snapshot([])
"""
    )

    e = e.format()

    assert e.is_formatted()

    e = e.with_files(
        {
            "pyproject.toml": """\
[tool.black]
line-length=50
"""
        }
    )

    assert e.is_formatted()

    e = e.run_pytest(
        ["--inline-snapshot=fix"],
        returncode=1,
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot


def test_a():
    assert list(range(10)) == snapshot(
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    )
"""
            }
        ),
    )

    assert e.is_formatted()


def test_disabled():
    e = Example(
        """\
from inline_snapshot import snapshot

def test_a():
    assert 4==snapshot(5)
"""
    )

    e.run_pytest(
        ["--inline-snapshot=disable"], outcomes=snapshot({"failed": 1}), returncode=1
    )

    e = e.run_pytest(["--inline-snapshot=fix"], returncode=1)

    assert e.files["tests/test_something.py"] == snapshot(
        """\
from inline_snapshot import snapshot

def test_a():
    assert 4==snapshot(4)
"""
    )

    e.run_pytest(["--inline-snapshot=disable"], outcomes=snapshot({"passed": 1}))


def test_compare():
    e = Example(
        """\
from inline_snapshot import snapshot

def test_a():
    assert "a"==snapshot("b")
"""
    )

    e.run_pytest(
        outcomes=snapshot({"failed": 1, "errors": 1}),
        error=snapshot(
            """\
>       assert "a"==snapshot("b")
E       AssertionError: assert 'a' == 'b'
E         \n\
E         - b
E         + a
"""
        ),
        returncode=1,
    )

    e = Example(
        """\
from inline_snapshot import snapshot

def test_a():
    assert snapshot("b")=="a"
"""
    )

    e.run_pytest(
        outcomes=snapshot({"failed": 1, "errors": 1}),
        error=snapshot(
            """\
>       assert snapshot("b")=="a"
E       AssertionError: assert 'b' == 'a'
E         \n\
E         - a
E         + b
"""
        ),
        returncode=1,
    )


def test_assertion_error_loop():
    Example(
        """\
from inline_snapshot import snapshot

for e in (1, 2):
    assert e == snapshot()
"""
    ).run_pytest(
        outcomes=snapshot({"errors": 1}),
        error=snapshot(
            """\
E   assert 2 == 1
E    +  where 1 = snapshot()
"""
        ),
        returncode=2,
    )


def test_assertion_error_multiple():
    Example(
        """\
from inline_snapshot import snapshot

for e in (1, 2):
    assert e == snapshot(1)
"""
    ).run_pytest(
        outcomes=snapshot({"errors": 1}),
        error=snapshot(
            """\
E   assert 2 == 1
E    +  where 1 = snapshot(1)
"""
        ),
        returncode=2,
    )


def test_assertion_error():
    Example(
        """\
from inline_snapshot import snapshot

assert 2 == snapshot(1)\
"""
    ).run_pytest(
        outcomes=snapshot({"errors": 1}),
        error=snapshot(
            """\
E   assert 2 == 1
E    +  where 1 = snapshot(1)
"""
        ),
        returncode=2,
    )


@pytest.mark.no_rewriting
def test_run_without_pytest(pytester):
    # snapshots are deactivated by default
    pytester.makepyfile(
        test_file="""
from inline_snapshot import snapshot
s=snapshot([1,2])
assert isinstance(s,list)
assert s==[1,2]
"""
    )

    result = pytester.runpython("test_file.py")

    assert result.ret == 0


def test_pytest_inlinesnapshot_auto():
    Example(
        """\
from inline_snapshot import snapshot

def test_something():
    assert 2 == snapshot(1)
"""
    ).run_pytest(
        ["--inline-snapshot=review"],
        stdin=b"y\n",
        outcomes=snapshot({"passed": 1, "errors": 1}),
        error=snapshot("\n"),
        report=snapshot(
            """\
-------------------------------- Fix snapshots ---------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -1,4 +1,4 @@                                                              |
|                                                                              |
|  from inline_snapshot import snapshot                                        |
|                                                                              |
|  def test_something():                                                       |
| -    assert 2 == snapshot(1)                                                 |
| +    assert 2 == snapshot(2)                                                 |
+------------------------------------------------------------------------------+
Do you want to fix these snapshots? [y/n] (n):\
"""
        ),
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_something():
    assert 2 == snapshot(2)
"""
            }
        ),
        returncode=1,
    )


def test_empty_sub_snapshot():
    Example(
        """\
from inline_snapshot import snapshot

def test_sub_snapshot():
    assert 1==snapshot({})["key"]
"""
    ).run_pytest(
        ["--inline-snapshot=short-report"],
        returncode=1,
        outcomes=snapshot({"passed": 1, "errors": 1}),
        report=snapshot(
            """\
Error: one snapshot is missing a value (--inline-snapshot=create)
You can also use --inline-snapshot=review to approve the changes interactively\
"""
        ),
    )


def test_persist_unknown_external():
    Example(
        """\
from inline_snapshot import external, snapshot

def test_sub_snapshot():
    external("hash:123*.png")
    assert 1==snapshot(2)
"""
    ).run_pytest(
        ["--inline-snapshot=fix"],
        outcomes=snapshot({"passed": 1, "errors": 1}),
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import external, snapshot

def test_sub_snapshot():
    external("hash:123*.png")
    assert 1==snapshot(1)
"""
            }
        ),
        returncode=1,
    )


def test_diff_multiple_files():

    Example(
        {
            "tests/test_a.py": """
from inline_snapshot import snapshot

def test_a():
    assert 1==snapshot(2)
    """,
            "tests/test_b.py": """
from inline_snapshot import snapshot

def test_b():
    assert 1==snapshot()
    """,
        }
    ).run_pytest(
        ["--inline-snapshot=create,fix"],
        changed_files=snapshot(
            {
                "tests/test_a.py": """\

from inline_snapshot import snapshot

def test_a():
    assert 1==snapshot(1)
    \
""",
                "tests/test_b.py": """\

from inline_snapshot import snapshot

def test_b():
    assert 1==snapshot(1)
    \
""",
            }
        ),
        report=snapshot(
            """\
------------------------------- Create snapshots -------------------------------
+------------------------------ tests/test_b.py -------------------------------+
| @@ -2,5 +2,5 @@                                                              |
|                                                                              |
|  from inline_snapshot import snapshot                                        |
|                                                                              |
|  def test_b():                                                               |
| -    assert 1==snapshot()                                                    |
| +    assert 1==snapshot(1)                                                   |
+------------------------------------------------------------------------------+
These changes will be applied, because you used create
-------------------------------- Fix snapshots ---------------------------------
+------------------------------ tests/test_a.py -------------------------------+
| @@ -2,5 +2,5 @@                                                              |
|                                                                              |
|  from inline_snapshot import snapshot                                        |
|                                                                              |
|  def test_a():                                                               |
| -    assert 1==snapshot(2)                                                   |
| +    assert 1==snapshot(1)                                                   |
+------------------------------------------------------------------------------+
These changes will be applied, because you used fix\
"""
        ),
        returncode=1,
    )


def test_equal_check():

    Example(
        {
            "test_a.py": """
from inline_snapshot import snapshot

class Thing:
    def __repr__(self):
        return "Thing()"

def test_a():
    assert Thing()==snapshot()
    """,
        }
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot({}),
        raises=snapshot(
            """\
UsageError:
inline-snapshot uses `copy.deepcopy` to copy objects,
but the copied object is not equal to the original one:

value = Thing()
copied_value = copy.deepcopy(value)
assert value == copied_value

Please fix the way your object is copied or your __eq__ implementation.
"""
        ),
    )


def test_equal_check_2():

    Example(
        {
            "test_a.py": """
from inline_snapshot import snapshot

class A:
    def __eq__(self,other):
        if isinstance(other,A):
            return False
        return NotImplemented

    def __repr__(self):
        return "A()"

def test_a():
    assert A() == snapshot(A())
    """,
        }
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot({}),
        raises=snapshot(
            """\
UsageError:
inline-snapshot uses `copy.deepcopy` to copy objects,
but the copied object is not equal to the original one:

value = A()
copied_value = copy.deepcopy(value)
assert value == copied_value

Please fix the way your object is copied or your __eq__ implementation.
"""
        ),
    )


def test_unknown_flag():

    e = Example(
        """\
def test_a():
    assert 1==1
"""
    )

    error = snapshot("ERROR: --inline-snapshot=creaigflen is a unknown flag\n")

    e.run_pytest(
        ["--inline-snapshot=creaigflen"],
        report=snapshot(""),
        returncode=snapshot(4),
        stderr=error,
    )

    e.run_inline(["--inline-snapshot=creaigflen"], stderr=error)


@pytest.mark.parametrize("storage_dir", ["tests/snapshots", None])
def test_storage_dir_config(tmp_path, storage_dir):
    # Relative path case: `tests/snapshots` (parametrized).
    # Absolute path case: `tmp_path / "snapshots"` (parametrized as `None`).
    relative = storage_dir is not None

    if not storage_dir:
        storage_dir = tmp_path / "snapshots"

    external_value = snapshot("hello")

    Example(
        {
            "pyproject.toml": f"""\
[tool.inline-snapshot]
storage-dir = {str(storage_dir)!r}
default-storage="hash"
""",
            "tests/test_a.py": """\
from inline_snapshot import outsource, snapshot

def test_outsource():
    assert outsource("hello") == snapshot()
""",
        }
    ).run_pytest(
        ["--inline-snapshot=create"],
        changed_files=IsIgnoreDict(
            {
                "tests/test_a.py": snapshot(
                    """\
from inline_snapshot import outsource, snapshot

from inline_snapshot import external

def test_outsource():
    assert outsource("hello") == snapshot(external("hash:2cf24dba5fb0*.txt"))
"""
                ),
                "tests/snapshots/external/2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824.txt": (
                    external_value if relative else None
                ),
            }
        ),
        returncode=1,
    ).run_pytest(
        ["--inline-snapshot=disable"], changed_files=snapshot({})
    ).run_pytest(
        ["--inline-snapshot=fix"], changed_files=snapshot({})
    )

    # assert result.ret == 0

    if not relative:
        assert {
            p.name: p.read_text() for p in (Path(storage_dir) / "external").iterdir()
        } == snapshot(
            {
                ".gitignore": """\
# ignore all snapshots which are not referred in the source
*-new.*
""",
                "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824.txt": external_value,
            }
        )


def test_find_pyproject_in_parent_directories():

    Example(
        {
            "pyproject.toml": """\
[tool.inline-snapshot]
hash-length=2
default-storage="hash"
""",
            "project/pytest.ini": "",
            "project/test_something.py": """\
from inline_snapshot import outsource,snapshot,external

def test_something():
    assert outsource("test") == snapshot()
""",
        }
    ).run_pytest(
        ["--rootdir", "./project", "--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "project/.inline-snapshot/external/9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08.txt": "test",
                "project/test_something.py": """\
from inline_snapshot import outsource,snapshot,external

def test_something():
    assert outsource("test") == snapshot(external("hash:9f*.txt"))
""",
            }
        ),
        returncode=1,
    )


def test_find_pyproject_in_workspace_project():

    Example(
        {
            "sub_project/pyproject.toml": """\
[tool.inline-snapshot]
hash-length=2
default-storage="hash"
""",
            "pyproject.toml": "[tool.pytest.ini_options]",
            "sub_project/test_something.py": """\
from inline_snapshot import outsource,snapshot,external

def test_something():
    assert outsource("test") == snapshot()
""",
        }
    ).run_pytest(
        ["--rootdir", "./sub_project", "--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "sub_project/.inline-snapshot/external/9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08.txt": "test",
                "sub_project/test_something.py": """\
from inline_snapshot import outsource,snapshot,external

def test_something():
    assert outsource("test") == snapshot(external("hash:9f*.txt"))
""",
            }
        ),
        returncode=1,
    )


@pytest.mark.xfail(
    not is_pytest_compatible(), reason="this works only for cpython >=3.11"
)
def test_default_report():

    Example(
        """\
import pytest
from inline_snapshot import snapshot

def test_a():
    assert 1==snapshot(5)
"""
    ).run_pytest(
        report=snapshot(
            """\
-------------------------------- Fix snapshots ---------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -2,4 +2,4 @@                                                              |
|                                                                              |
|  from inline_snapshot import snapshot                                        |
|                                                                              |
|  def test_a():                                                               |
| -    assert 1==snapshot(5)                                                   |
| +    assert 1==snapshot(1)                                                   |
+------------------------------------------------------------------------------+
These changes are not applied.
Use --inline-snapshot=fix to apply them, or use the interactive mode with
--inline-snapshot=review\
"""
        ),
        returncode=snapshot(1),
        stderr=snapshot(""),
        changed_files=snapshot({}),
    )


@pytest.mark.xfail(
    not is_pytest_compatible(), reason="this works only for cpython >=3.11"
)
def test_default_review():

    Example(
        """\
import pytest
from inline_snapshot import snapshot

def test_a():
    assert 1==snapshot(5)
"""
    ).run_pytest(
        report=snapshot(
            """\
-------------------------------- Fix snapshots ---------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -2,4 +2,4 @@                                                              |
|                                                                              |
|  from inline_snapshot import snapshot                                        |
|                                                                              |
|  def test_a():                                                               |
| -    assert 1==snapshot(5)                                                   |
| +    assert 1==snapshot(1)                                                   |
+------------------------------------------------------------------------------+
Do you want to fix these snapshots? [y/n] (n):\
"""
        ),
        returncode=snapshot(1),
        stderr=snapshot(""),
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
import pytest
from inline_snapshot import snapshot

def test_a():
    assert 1==snapshot(1)
"""
            }
        ),
        stdin=b"y\n",
    )


def test_pytest_configure_exception():

    Example(
        {
            "conftest.py": """
import pytest
def pytest_configure(config: pytest.Config) -> None:

    pytest.exit(
        reason="failed",
        returncode=pytest.ExitCode.INTERRUPTED,
    )
""",
            "test_a.py": """
def test_a():
    pass
             """,
        }
    ).run_pytest(stderr=snapshot("Exit: failed"), returncode=snapshot(2))
