## Only CPython is supported

Currently, inline-snapshot only works with CPython.
On other Python implementations, such as PyPy, inline-snapshot acts as if `--inline-snapshot=disable` is set, allowing tests to pass but not providing any way to update snapshots.

## pytest-xdist is not supported

[pytest-xdist](https://pytest-xdist.readthedocs.io/) splits test runs across multiple processes.
This prevents inline-snapshot from being able to update snapshots across multiple processes, so if you have pytest-xdist installed and active, inline-snapshot will act as if `--inline-snapshot=disable` is set.

If you have pytest-xdist installed and active by default in your pytest settings, you can disable it for a single test run with [its `-n0` option](https://pytest-xdist.readthedocs.io/en/stable/distribution.html).
Then inline-snapshot will act as usual, or you can pass alternative flags with `--inline-snapshot`:

```bash
pytest -n0 --inline-snapshot=create,report
```

## On CPython < 3.11, pytest assert rewriting can be disabled [](){#pytest-assert-rewriting-is-disabled}

On CPython versions before 3.11, inline-snapshot must disable pytest assert rewriting if you use any of these flags: `report`, `review`, `create`, `fix`, `trim`, or `update`.
