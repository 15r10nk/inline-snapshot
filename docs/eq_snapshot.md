## General

A snapshot can be compared against any value with `==`.
The value gets recorded if the snapshot is undefined (`snapshot()`)

Example:

=== "original code"
    <!-- inline-snapshot: outcome-passed=1 outcome-errors=1 -->
    ```python
    def test_something():
        assert 2 + 2 == snapshot()
    ```

=== "--inline-snapshot=create"
    <!-- inline-snapshot: create -->
    ```python
    def test_something():
        assert 2 + 2 == snapshot(4)
    ```

## pytest options

It interacts with the following `--inline-snapshot` flags:

- `create` create a new value if the snapshot value is undefined.
- `fix` record the new value and store it in the source code if it is different from the current one.
