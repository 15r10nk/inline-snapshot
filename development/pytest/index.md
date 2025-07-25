inline-snapshot provides one pytest option with different flags (*create*, *fix*, *trim*, *update*, *short-report*, *report*, *disable*).

Snapshot comparisons return always `True` if you use one of the flags *create*, *fix* or *review*. This is necessary because the whole test needs to be run to fix all snapshots like in this case:

```
from inline_snapshot import snapshot


def test_something():
    assert 1 == snapshot(5)
    assert 2 <= snapshot(5)

```

Note

Every flag with the exception of *disable* and *short-report* disables the pytest assert-rewriting.

## --inline-snapshot=create,fix,trim,update

Approve the changes of the given [category](../categories/). These flags can be combined with *report* and *review*.

test_something.py

```
from inline_snapshot import snapshot


def test_something():
    assert 1 == snapshot()
    assert 2 <= snapshot(5)

```

```
> pytest test_something.py --inline-snapshot=create,report
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-8.4.1, pluggy-1.6.0
rootdir: /tmp/tmp.IpamWzOUi5
plugins: inline-snapshot-0.25.2
collected 1 item

test_something.py .E                                                     [100%]

═══════════════════════════════ inline-snapshot ════════════════════════════════
─────────────────────────────── Create snapshots ───────────────────────────────
╭───────────────────────────── test_something.py ──────────────────────────────╮
│ @@ -2,5 +2,5 @@                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│  def test_something():                                                       │
│ -    assert 1 == snapshot()                                                  │
│ +    assert 1 == snapshot(1)                                                 │
│      assert 2 <= snapshot(5)                                                 │
╰──────────────────────────────────────────────────────────────────────────────╯
These changes will be applied, because you used ]8;id=218700;https://15r10nk.github.io/inline-snapshot/latest/categories/#create\create]8;;\

──────────────────────────────── Trim snapshots ────────────────────────────────
╭───────────────────────────── test_something.py ──────────────────────────────╮
│ @@ -3,4 +3,4 @@                                                              │
│                                                                              │
│                                                                              │
│  def test_something():                                                       │
│      assert 1 == snapshot(1)                                                 │
│ -    assert 2 <= snapshot(5)                                                 │
│ +    assert 2 <= snapshot(2)                                                 │
╰──────────────────────────────────────────────────────────────────────────────╯
These changes are not applied.
Use --inline-snapshot=]8;id=899625;https://15r10nk.github.io/inline-snapshot/latest/categories/#trim\trim]8;;\ to apply them, or use the interactive mode with 
--inline-snapshot=]8;id=120729;https://15r10nk.github.io/inline-snapshot/latest/pytest/#-inline-snapshotreview\review]8;;\



==================================== ERRORS ====================================
_____________________ ERROR at teardown of test_something ______________________
your snapshot is missing one value.
If you just created this value with --snapshot=create, the value is now created and you can ignore this message.
=========================== short test summary info ============================
ERROR test_something.py::test_something - Failed: your snapshot is missing one value.
========================== 1 passed, 1 error in 0.10s ==========================

```

## --inline-snapshot=short-report

give a short report over which changes can be made to the snapshots

```
> pytest test_something.py --inline-snapshot=short-report
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-8.4.1, pluggy-1.6.0
rootdir: /tmp/tmp.J15BNfIJ5a
plugins: inline-snapshot-0.25.2
collected 1 item

test_something.py .E                                                     [100%]

═══════════════════════════════ inline-snapshot ════════════════════════════════
Info: one snapshot can be trimmed (--inline-snapshot=trim)
Error: one snapshot is missing a value (--inline-snapshot=create)

You can also use --inline-snapshot=review to approve the changes interactively


==================================== ERRORS ====================================
_____________________ ERROR at teardown of test_something ______________________
your snapshot is missing one value.
If you just created this value with --snapshot=create, the value is now created and you can ignore this message.
=========================== short test summary info ============================
ERROR test_something.py::test_something - Failed: your snapshot is missing one value.
========================== 1 passed, 1 error in 0.09s ==========================

```

Info

short-report exists mainly to show that snapshots have changed with enabled pytest assert-rewriting. This option will be replaced with *report* when this restriction is lifted.

## --inline-snapshot=report

Shows a diff report over which changes can be made to the snapshots

```
> pytest test_something.py --inline-snapshot=report
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-8.4.1, pluggy-1.6.0
rootdir: /tmp/tmp.OJkLwBIldf
plugins: inline-snapshot-0.25.2
collected 1 item

test_something.py .E                                                     [100%]

═══════════════════════════════ inline-snapshot ════════════════════════════════
─────────────────────────────── Create snapshots ───────────────────────────────
╭───────────────────────────── test_something.py ──────────────────────────────╮
│ @@ -2,5 +2,5 @@                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│  def test_something():                                                       │
│ -    assert 1 == snapshot()                                                  │
│ +    assert 1 == snapshot(1)                                                 │
│      assert 2 <= snapshot(5)                                                 │
╰──────────────────────────────────────────────────────────────────────────────╯
These changes are not applied.
Use --inline-snapshot=]8;id=595910;https://15r10nk.github.io/inline-snapshot/latest/categories/#create\create]8;;\ to apply them, or use the interactive mode with 
--inline-snapshot=]8;id=873347;https://15r10nk.github.io/inline-snapshot/latest/pytest/#-inline-snapshotreview\review]8;;\

──────────────────────────────── Trim snapshots ────────────────────────────────
╭───────────────────────────── test_something.py ──────────────────────────────╮
│ @@ -3,4 +3,4 @@                                                              │
│                                                                              │
│                                                                              │
│  def test_something():                                                       │
│      assert 1 == snapshot()                                                  │
│ -    assert 2 <= snapshot(5)                                                 │
│ +    assert 2 <= snapshot(2)                                                 │
╰──────────────────────────────────────────────────────────────────────────────╯
These changes are not applied.
Use --inline-snapshot=]8;id=505048;https://15r10nk.github.io/inline-snapshot/latest/categories/#trim\trim]8;;\ to apply them, or use the interactive mode with 
--inline-snapshot=]8;id=640806;https://15r10nk.github.io/inline-snapshot/latest/pytest/#-inline-snapshotreview\review]8;;\



==================================== ERRORS ====================================
_____________________ ERROR at teardown of test_something ______________________
your snapshot is missing one value.
If you just created this value with --snapshot=create, the value is now created and you can ignore this message.
=========================== short test summary info ============================
ERROR test_something.py::test_something - Failed: your snapshot is missing one value.
========================== 1 passed, 1 error in 0.10s ==========================

```

## --inline-snapshot=review

Shows a diff report for each category and ask if you want to apply the changes

```
> pytest test_something.py --inline-snapshot=review
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-8.4.1, pluggy-1.6.0
rootdir: /tmp/tmp.QptKxSH3eU
plugins: inline-snapshot-0.25.2
collected 1 item

test_something.py .E                                                     [100%]

═══════════════════════════════ inline-snapshot ════════════════════════════════
─────────────────────────────── Create snapshots ───────────────────────────────
╭───────────────────────────── test_something.py ──────────────────────────────╮
│ @@ -2,5 +2,5 @@                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│  def test_something():                                                       │
│ -    assert 1 == snapshot()                                                  │
│ +    assert 1 == snapshot(1)                                                 │
│      assert 2 <= snapshot(5)                                                 │
╰──────────────────────────────────────────────────────────────────────────────╯
Do you want to ]8;id=542322;https://15r10nk.github.io/inline-snapshot/latest/categories/#create\create]8;;\ these snapshots? [y/n] (n): 
──────────────────────────────── Trim snapshots ────────────────────────────────
╭───────────────────────────── test_something.py ──────────────────────────────╮
│ @@ -3,4 +3,4 @@                                                              │
│                                                                              │
│                                                                              │
│  def test_something():                                                       │
│      assert 1 == snapshot(1)                                                 │
│ -    assert 2 <= snapshot(5)                                                 │
│ +    assert 2 <= snapshot(2)                                                 │
╰──────────────────────────────────────────────────────────────────────────────╯
Do you want to ]8;id=397227;https://15r10nk.github.io/inline-snapshot/latest/categories/#trim\trim]8;;\ these snapshots? [y/n] (n): 


==================================== ERRORS ====================================
_____________________ ERROR at teardown of test_something ______________________
your snapshot is missing one value.
If you just created this value with --snapshot=create, the value is now created and you can ignore this message.
=========================== short test summary info ============================
ERROR test_something.py::test_something - Failed: your snapshot is missing one value.
========================== 1 passed, 1 error in 0.10s ==========================

```

## --inline-snapshot=disable

Disables all the snapshot logic. `snapshot(x)` will just return `x` and inline-snapshot will not be able to fix snapshots or to generate reports. This can be used if you think that snapshot logic causes a problem in your tests. It is also the default for CI runs.

deprecation

This option was previously called `--inline-snapshot-disable`
