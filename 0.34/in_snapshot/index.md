## General

It is possible to check if an value is in a snapshot. The value of the generated snapshot will be a list of all values which are tested.

Example:

```
from inline_snapshot import snapshot


def test_something():
    s = snapshot()

    assert 5 in s
    assert 5 in s
    assert 8 in s

    for v in ["a", "b"]:
        assert v in s
```

```
from inline_snapshot import snapshot


def test_something():
    s = snapshot([5, 8, "a", "b"])

    assert 5 in s
    assert 5 in s
    assert 8 in s

    for v in ["a", "b"]:
        assert v in s
```

## pytest options

It interacts with the following `--inline-snapshot` flags:

- `create` create a new value if the snapshot value is undefined.
- `fix` adds a value to the list if it is missing.
- `trim` removes a value from the list if it is not necessary.
