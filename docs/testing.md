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
    ).run_inline(  # run without flags
        reported_categories=snapshot(),
    ).run_pytest(
        ["--inline-snapshot=short-report"],  # check the pytest report
        changed_files=snapshot(),
        report=snapshot(),
        returncode=snapshot(),
    ).run_pytest(  # run with the create flag and check the changed files
        ["--inline-snapshot=create"],
        changed_files=snapshot(),
        returncode=snapshot(),
    )
```

Inline-snapshot will then populate the empty snapshots.

<!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
``` python hl_lines="16 19 20 21 22 23 24 25 26 29 30 31 32 33 34 35 36 37 38"
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
    ).run_inline(  # run without flags
        reported_categories=snapshot(["create"]),
    ).run_pytest(
        ["--inline-snapshot=short-report"],  # check the pytest report
        changed_files=snapshot({}),
        report=snapshot(
            """\
Error: one snapshot is missing a value (--inline-snapshot=create)
You can also use --inline-snapshot=review to approve the changes interactively\
"""
        ),
        returncode=snapshot(1),
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

The `Example` class stores the given files and creates the test environment every time you call a `run_*` method. This means that you can create an `Example` and call the `run_*` methods on it in the order you want with the arguments that are useful for your test case.
The result of the `run_*` method is always a new `Example` object with the updated files.

## API
::: inline_snapshot.testing.Example
    options:
      heading_level: 3
      show_root_heading: true
      show_root_full_path: false
      show_source: false
      annotations_path: brief
