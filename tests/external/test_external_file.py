from inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


def test_external_file():

    Example(
        """\
from inline_snapshot import external_file

def test_a():
    assert "test1".upper() == external_file("test.txt"), "not equal"
"""
    ).run_inline(
        raises=snapshot(
            """\
AssertionError:
not equal\
"""
        )
    ).run_pytest(
        ["--inline-snapshot=create"],
        changed_files=snapshot({"tests/test.txt": "TEST1"}),
        report=snapshot(
            """\
+------------------------------- tests/test.txt -------------------------------+
| TEST1                                                                        |
+------------------------------------------------------------------------------+
These changes will be applied, because you used create\
"""
        ),
        returncode=snapshot(1),
    ).replace(
        "test1", "test2"
    ).run_inline(
        ["--inline-snapshot=disable"],
        raises=snapshot(
            """\
AssertionError:
not equal\
"""
        ),
    ).run_pytest(
        ["--inline-snapshot=fix"],
        changed_files=snapshot({"tests/test.txt": "TEST2"}),
        report=snapshot(
            """\
+------------------------------- tests/test.txt -------------------------------+
| @@ -1 +1 @@                                                                  |
|                                                                              |
| -TEST1                                                                       |
| +TEST2                                                                       |
+------------------------------------------------------------------------------+
These changes will be applied, because you used fix\
"""
        ),
        returncode=snapshot(1),
    )


def test_compare_twice():

    Example(
        """\
from inline_snapshot import external_file

def test_a():
    assert "test1" == external_file("test.txt"), "not equal"
    assert "test1" == external_file("test.txt"), "not equal"
"""
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot({"tests/test.txt": "test1"}),
    ).run_inline()


def test_external_in_other_dir(tmp_path):

    file = tmp_path / "subdir" / "subsubdir" / "file.txt"
    print("file", file)

    Example(
        f"""\
from inline_snapshot import external_file

def test_a():
    assert "test" == external_file({str(file)!r})

"""
    ).run_pytest(
        ["--inline-snapshot=create"], changed_files=snapshot({}), returncode=1
    ).run_inline()

    assert file.read_text() == "test"


def test_unused_external_file():

    Example(
        f"""\
from inline_snapshot import external_file

def test_a():
    external_file("test.txt")

"""
    ).run_inline(["--inline-snapshot=create"], changed_files=snapshot({})).run_inline()


def test_register_format_alias():

    Example(
        f"""\
from inline_snapshot import external_file,register_format_alias

register_format_alias(".html",".txt")

def test_bar():
    assert "text" ==external_file("a.html")
    """
    ).run_inline(
        ["--inline-snapshot=create"], changed_files=snapshot({"tests/a.html": "text"})
    )


def test_report():
    # see https://github.com/15r10nk/inline-snapshot/issues/298

    Example(
        """\

from inline_snapshot import external_file


def test_example():
    n=5
    assert sorted([n, 2]) == external_file("stored.json")


"""
    ).run_pytest(
        ["--inline-snapshot=report"],
        report=snapshot(
            """\
+----------------------------- tests/stored.json ------------------------------+
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
                "tests/stored.json": """\
[
  2,
  5
]\
"""
            }
        ),
    ).replace(
        "n=5", "n=8"
    ).run_pytest(
        ["--inline-snapshot=report"],
        report=snapshot(
            """\
+----------------------------- tests/stored.json ------------------------------+
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
