## General

A snapshot can be compared against any value with `==`.
The value gets recorded if the snapshot is undefined (`snapshot()`)

Example:

<!-- inline-snapshot: update this -->
```python
def test_something():
    assert 2 + 2 == snapshot(4)
```

## pytest options

It interacts with the following `--inline-snapshot` flags:

- `create` create a new value if the snapshot value is undefined.
- `fix` record the new value and store it in the source code if it is different from the current one.
