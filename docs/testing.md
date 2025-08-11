`inline_snapshot.testing` provides tools that can be used to test inline-snapshot workflows.
This might be useful if you want to build your own libraries based on inline-snapshot.

The following example shows how you can use the `Example` class to test what inline-snapshot would do with the given source code. The snapshots in the argument are asserted inside the `run_*` methods. Some arguments are optional, and some are required. Please see the reference below for details.

<!-- inline-snapshot: first_block outcome-passed=1 outcome-errors=1 -->
``` python
from inline_snapshot.testing import Example
from inline_snapshot import snapshot


def test_something():

    Example(
        {
            "test_a.py": """\
from inline_snapshot import snapshot
def test_a():
    assert 1+1 == snapshot()
"""
        }
    ).run_pytest(  # run with the create flag and check the changed files
        ["--inline-snapshot=create"],
        changed_files=snapshot(),
        returncode=snapshot(),
    )
```

Inline-snapshot will then populate the empty snapshots.

<!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
``` python hl_lines="17 18 19 20 21 22 23 24 25 26"
from inline_snapshot.testing import Example
from inline_snapshot import snapshot


def test_something():

    Example(
        {
            "test_a.py": """\
from inline_snapshot import snapshot
def test_a():
    assert 1+1 == snapshot()
"""
        }
    ).run_pytest(  # run with the create flag and check the changed files
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "test_a.py": """\
from inline_snapshot import snapshot
def test_a():
    assert 1+1 == snapshot(2)
"""
            }
        ),
        returncode=snapshot(1),
    )
```

The `Example` object is immutable and not connected to any directory.
A temporary directory is only created when you call a `run_*` method.
The result of the `run_*` method is always a new `Example` object with the updated files.
This means that you can create an `Example` and call the `run_*` methods on it in any order you want, with the arguments that are useful for your test case.

This allows for more complex tests where you create one example and perform multiple test runs on it. Every test run will work on the changed files from the previous one.

<!-- inline-snapshot: create fix first_block outcome-passed=1 -->
``` python
from inline_snapshot.testing import Example
from inline_snapshot import snapshot


def test_something():

    Example(
        {
            "test_a.py": """\
from inline_snapshot import snapshot
def test_a():
    assert 1+1 == snapshot()
    assert 1+5 == snapshot(2)
"""
        }
    ).run_pytest(  # run with the create flag and check the changed files
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "test_a.py": """\
from inline_snapshot import snapshot
def test_a():
    assert 1+1 == snapshot(2)
    assert 1+5 == snapshot(2)
"""
            }
        ),
        returncode=snapshot(1),
    ).run_pytest(  # run with the create flag and check the changed files
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "test_a.py": """\
from inline_snapshot import snapshot
def test_a():
    assert 1+1 == snapshot(2)
    assert 1+5 == snapshot(6)
"""
            }
        ),
        returncode=snapshot(1),
    )
```

You can also use the same example multiple times and call different methods on it.

<!-- inline-snapshot: create fix first_block outcome-failed=1 -->
``` python
from inline_snapshot.testing import Example
from inline_snapshot import snapshot


def test_something():

    e = Example(
        {
            "test_a.py": """\
from inline_snapshot import snapshot
def test_a():
    assert 1+1 == snapshot()
    assert 1+5 == snapshot(2)
"""
        }
    )
    e.run_inline(  # run without flags
        reported_categories=snapshot(["create", "fix"]),
    )

    e.run_pytest(
        ["--inline-snapshot=short-report"],  # check the pytest report
        changed_files=snapshot({}),
        report=snapshot(
            """\
Error: one snapshot is missing a value (--inline-snapshot=create)
You can also use --inline-snapshot=review to approve the changes interactively\
"""
        ),
        returncode=snapshot(1),
    )
    e.run_pytest(  # run with the create flag and check the changed files
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "test_a.py": """\
from inline_snapshot import snapshot
def test_a():
    assert 1+1 == snapshot(2)
"""
            }
        ),
        returncode=snapshot(1),
    )
```

## API
::: inline_snapshot.testing.Example
    options:
      heading_level: 3
      show_root_heading: true
      show_root_full_path: false
      show_source: false
      annotations_path: brief
