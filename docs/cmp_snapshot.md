## General

A snapshot can be compared against any value with `<=` or `>=`.
This can be used to create a upper/lower bound for some result.

Example:

<!-- inline-snapshot: update this -->
```python
def some_algo():
    ...
    result = 42
    iterations = 2
    ...
    return result, iterations


def test_something():
    result, iterations = some_algo()

    assert result == snapshot(42)
    assert iterations <= snapshot(2)
```

!!! warning
    This should not be used to check for any flaky values like the runtime of some code, because it will randomly break your tests.

The same snapshot value can also be used in multiple assertions.
The snapshot value in the following case would be `6`.

<!-- inline-snapshot: outcome-errors=1 outcome-passed=1 -->
```python
def test_something():
    value = snapshot()

    assert 5 <= value
    assert 6 <= value
```

## pytest options

It interacts with the following `--inline-snapshot` flags:

- `create` create a new value if the snapshot value is undefined.
- `fix` record the new value and store it in the source code if it is contradicts the comparison.
- `trim` record the new value and store it in the source code if it is more strict than the old one.
