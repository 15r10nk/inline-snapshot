
inline-snapshot comes with a pytest plugin which offers the following options.


### --inline-snapshot=...
- **--inline-snapshot=create**:
    creates snapshots which are currently not defined
- **--inline-snapshot=update**:
    update snapshots if they changed their representation (result of `repr()`)
- **--inline-snapshot=trim**:
    changes the snapshot in a way which will make the snapshot more precise.
- **--inline-snapshot=fix**:
    change snapshots which are currently breaking your tests (where the result of the snapshot operation is `False`).

It is also possible to provide multiple flags at once:

``` bash
pytest --inline-snapshot=trim,fix
```

### --inline-snapshot-disable
    disable all the snapshot logic. `snapshot(x)` will just return `x`.
