
inline-snapshot comes with a pytest plugin which offers the following options.



### --inline-snapshot=...
- **--inline-snapshot=create**:
    creates snapshots which are currently not defined
- **--inline-snapshot=update**:
    update snapshots if they changed their representation (result of `repr()`)
- **--inline-snapshot=trim**:
    changes the snapshot in a way which will make the snapshot more precise (see [`value in snapshot()`](in_snapshot.md) and [`snapshot()[key]`](getitem_snapshot.md) ).


- **--inline-snapshot=fix**:
    change snapshots which are currently breaking your tests (where the result of the snapshot operation is `False`).


This allows you to control which snapshots you want to modify.

=== "original code"

    <!-- inline-snapshot: outcome-errors=1 outcome-passed=1 -->
    ```python
    def test_something():
        assert 7 <= snapshot(10)  # only changed with trim
        assert 5 <= snapshot()  # only changed with create
    ```


=== "--inline-snapshot=create"

    <!-- inline-snapshot: create -->
    ```python
    def test_something():
        assert 7 <= snapshot(10)  # only changed with trim
        assert 5 <= snapshot(5)  # only changed with create
    ```

=== "--inline-snapshot=trim"

    <!-- inline-snapshot: trim -->
    ```python
    def test_something():
        assert 7 <= snapshot(7)  # only changed with trim
        assert 5 <= snapshot(5)  # only changed with create
    ```


It is also possible to provide multiple flags at once:

``` bash
pytest --inline-snapshot=trim,fix
```

### --inline-snapshot-disable

Disables all the snapshot logic. `snapshot(x)` will just return `x`.
