

`inline_snapshot.testing` provides tools which can be used to test inline-snapshot workflows.
This might be useful if you want to build your own libraries based on inline-snapshot.

The following example shows how you can use the `Example` class to test what inline-snapshot would do with given the source code. The snapshots in the argument are asserted inside the `run_*` methods, but only when they are provided.

=== "original"

    <!-- inline-snapshot: first_block outcome-failed=1 outcome-errors=1 -->
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
        ).run_pytest(  # run with create flag and check the changed files
            ["--inline-snapshot=create"],
            changed_files=snapshot(),
        )
    ```

=== "--inline-snapshot=create"

    <!-- inline-snapshot: create outcome-failed=1 outcome-errors=1 -->
    ``` python hl_lines="16 19 20 21 22 23 24 25 26"
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
        ).run_pytest(  # run with create flag and check the changed files
            ["--inline-snapshot=create"],
            changed_files=snapshot(),
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
