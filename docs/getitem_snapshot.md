## General

It is possible to generate sub-snapshots during runtime.
This sub-snapshots can be used like a normal snapshot.

Example:

=== "original code"
    <!-- inline-snapshot: first_block outcome-passed=1 outcome-errors=1 -->
    ``` python
    from inline_snapshot import snapshot


    def test_something():
        s = snapshot()

        assert s["a"] == 4
        assert s["b"] == 5
    ```

=== "--inline-snapshot=create"
    <!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
    ``` python hl_lines="5"
    from inline_snapshot import snapshot


    def test_something():
        s = snapshot({"a": 4, "b": 5})

        assert s["a"] == 4
        assert s["b"] == 5
    ```

`s[key]` can be used with every normal snapshot operation including `s[key1][key2]`.


## pytest options

It interacts with the following `--inline-snapshot` flags:

- `create` create a new value if the snapshot value is undefined or create a new sub-snapshot if one is missing.
- `trim` remove sub-snapshots if they are not needed any more.

The flags `fix` and `update` are applied recursive to all sub-snapshots.
