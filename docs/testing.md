

`inline_snapshot.testing` provides tools which can be used to test inline-snapshot workflows.
This might be useful if you want to build your own libraries based on inline-snapshot.

The following example shows how you can use the `Example` class to test what inline-snapshot would do with given the source code. The snapshots in the argument are asserted inside the `run_*` methods, but only when they are provided.

=== "original"

    <!-- inline-snapshot: outcome-passed=1 outcome-errors=1 -->
    ```python
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
        ).run_inline(
            reported_flags=snapshot(),
        ).run_pytest(
            changed_files=snapshot(),
            report=snapshot(),
        ).run_pytest(
            ["--inline-snapshot=create"],
            changed_files=snapshot(),
        )
    ```

=== "--inline-snapshot=create"

    <!-- inline-snapshot: create outcome-passed=1 -->
    ```python
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
        ).run_inline(
            reported_flags=snapshot(["create"]),
        ).run_pytest(
            changed_files=snapshot({}),
            report=snapshot(
                """\
    Error: one snapshot is missing a value (--inline-snapshot=create)
    You can also use --inline-snapshot=review to approve the changes interactiv\
    """
            ),
        ).run_pytest(
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
        )
    ```


## API
::: inline_snapshot.testing.Example
    options:
      separate_signature: true
      show_signature_annotations: true


## Types

The following types are for type checking.

::: inline_snapshot.Category

see [categories](categories.md)

::: inline_snapshot.Snapshot

Can be used to annotate where snapshots can be passed as function arguments.

??? note "Example"
    <!-- inline-snapshot: create fix trim this outcome-passed=2 -->
    ```python
    from typing import Optional
    from inline_snapshot import snapshot, Snapshot


    def check_in_bounds(value, lower: Snapshot[int], upper: Snapshot[int]):
        assert lower <= value <= upper


    def test_numbers():
        for c in "hello world":
            check_in_bounds(ord(c), snapshot(32), snapshot(119))


    def check_container(
        value,
        *,
        value_repr: Optional[Snapshot[str]] = None,
        length: Optional[Snapshot[int]] = None
    ):
        if value_repr is not None:
            assert repr(value) == value_repr

        if length is not None:
            assert len(value) == length


    def test_container():
        check_container([1, 2], value_repr=snapshot("[1, 2]"), length=snapshot(2))

        check_container({1, 1}, length=snapshot(1))
    ```
