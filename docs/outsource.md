## General

!!! info
    This feature is currently under development. See this [issue](https://github.com/15r10nk/inline-snapshot/issues/86) for more information.

Storing snapshots in the source code is the main feature of inline snapshots.
This has the advantage that you can easily see changes in code reviews. But it also has some problems:

* It is problematic to snapshot a lot of data, because it takes up a lot of space in your tests.
* Binary data or images are not readable in your tests.

The `external()` solves this problem and integrates itself nicely with the inline snapshot.
It stores a reference to the external date in a special `external()` object which can be used like `snapshot()`.

There are different storage protocols like *hash* or *uuid* and different file formats like *.txt*, *.bin*, and *.json*. It is also possible to implement custom file formats.


Example:

=== "original code"
    <!-- inline-snapshot: first_block outcome-failed=1 outcome-errors=1 -->
    ``` python
    from inline_snapshot import external


    def test_something():
        assert "string" == external()
        assert b"bytes" == external()
        assert ["json", "like", "data"] == external(".json")
    ```

=== "--inline-snapshot=create"
    <!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
    ``` python hl_lines="5 6 7"
    from inline_snapshot import external


    def test_something():
        assert "string" == external("hash:473287f8298d*.txt")
        assert b"bytes" == external("hash:277089d91c0b*.bin")
        assert ["json", "like", "data"] == external("hash:e790f887ceac*.json")
    ```

The `external` object can be used inside other data structures.

=== "original code"
    <!-- inline-snapshot: first_block outcome-passed=1 outcome-errors=1 -->
    ``` python
    from inline_snapshot import snapshot, outsource


    def test_something():
        assert [
            outsource("long text\n" * times) for times in [50, 100, 1000]
        ] == snapshot()
    ```

=== "--inline-snapshot=create"
    <!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
    ``` python hl_lines="3 4 9 10 11 12 13 14 15"
    from inline_snapshot import snapshot, outsource

    from inline_snapshot import external


    def test_something():
        assert [
            outsource("long text\n" * times) for times in [50, 100, 1000]
        ] == snapshot(
            [
                external("hash:362ad8374ed6*.txt"),
                external("hash:5755afea3f8d*.txt"),
                external("hash:f5a956460453*.txt"),
            ]
        )
    ```


## API

::: inline_snapshot.outsource
    options:
      show_root_heading: true

::: inline_snapshot.external
    options:
      show_root_heading: true

## pytest options

It interacts with the following `--inline-snapshot` flags:

- `trim` removes every snapshots form the storage which is not referenced with `external(...)` in the code.
