# pytest

inline-snapshot provides a single pytest option with several flags (*create*, *fix*, *trim*, *update*, *short-report*, *report*, *review*, *disable*). You can also use inline-snapshot without any CLI options, in which case the [default flags](#default-flags) will be used.

Snapshot comparisons always return `True` when you use one of the flags *create*, *fix*, or *review*. This is necessary because the whole test needs to run before inline-snapshot can fix all snapshots, as in this example:

```
from inline_snapshot import snapshot


def test_something():
    assert 1 == snapshot(5)
    assert 2 <= snapshot(5)
```

Note

Every flag except *disable* and *short-report* disables pytest assertion rewriting for *CPython 3.10 or older*.

## --inline-snapshot=create,fix,trim,update

Approve the changes for the given [category](https://15r10nk.github.io/inline-snapshot/development/categories/index.md). These flags can be combined with *report* and *review*.

test_example.py

```
from inline_snapshot import snapshot


def test_something():
    assert 1 == snapshot()
    assert 2 <= snapshot(5)
```

`--inline-snapshot=create,report` creates the missing value and reports that `snapshot(5)` can be changed to `snapshot(2)` in two separate diffs.

## --inline-snapshot=short-report

Shows a short report of the changes that can be made to the snapshots.

Info

short-report exists mainly to show that snapshots have changed while pytest assertion rewriting is enabled. This option will be replaced with *report* when this restriction is lifted.

## --inline-snapshot=report

Shows a diff report of the changes that can be made to the snapshots.

## --inline-snapshot=review

Shows a diff report for each category and asks whether you want to apply the changes.

## --inline-snapshot=disable

Disables all snapshot logic. `snapshot(x)` will just return `x`, and inline-snapshot will not be able to fix snapshots or generate reports. This can be useful if you think that snapshot logic causes a problem in your tests. It is also the default for CI runs.

deprecation

This option was previously called `--inline-snapshot-disable`

## Default Flags

The [default flags](https://15r10nk.github.io/inline-snapshot/development/configuration/#default-flags) when you are in an interactive terminal are `--inline-snapshot=create,review` (or `--inline-snapshot=short-report` when you are using *CPython 3.10 or older*).

This allows you to work with pytest and inline-snapshot without changing your usual pytest workflow.
