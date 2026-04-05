
# snapshot_arg(...)

`snapshot_arg` lets you embed snapshot assertions inside a helper function, so callers don't need to pass `snapshot()` at every call site.
It is an advanced feature for integrating inline-snapshot more deeply into your tests or an existing testing framework.

Let's say you have some code like this where you have to pass `snapshot()` as an argument.

``` python
from inline_snapshot import snapshot


def check(data, min_value, max_value):
    assert min(data) == min_value
    assert max(data) == max_value


def test():
    check([1, 3], snapshot(), snapshot())
    check([5, 5], snapshot(), snapshot())
```

This works, but has a drawback: you have to pass `snapshot()` explicitly every time you call `check`.

`snapshot_arg` allows you to move the snapshot call into the function.

<!-- inline-snapshot: first_block outcome-passed=1 outcome-errors=1 -->
``` python
from inline_snapshot import snapshot_arg


def check(data, min_value=..., max_value=...):
    assert min(data) == snapshot_arg(min_value)
    assert max(data) == snapshot_arg(max_value)


def test_numbers():
    check([1, 3])
    check([5, 5])
```
The `...` act as placeholder defaults, so callers don't need to pass a value — inline-snapshot fills one in when you run `pytest`.

<!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
``` python hl_lines="10 11"
from inline_snapshot import snapshot_arg


def check(data, min_value=..., max_value=...):
    assert min(data) == snapshot_arg(min_value)
    assert max(data) == snapshot_arg(max_value)


def test_numbers():
    check([1, 3], min_value=1, max_value=3)
    check([5, 5], min_value=5, max_value=5)
```

Another benefit of `snapshot_arg` is support for real default values. inline-snapshot omits an argument at the call site when its value matches the default.

When the default is `...`, inline-snapshot uses the [*create*](categories.md#create) category to generate the initial value. When an other default is provided, it uses [*fix*](categories.md#fix) and creates the value only if the actual value differs from that default.

The following example uses default values. It evaluates a Python expression and records the result or any exception raised:

<!-- inline-snapshot: first_block outcome-failed=1 outcome-errors=1 -->
``` python
from inline_snapshot import snapshot_arg


def eval_expr(expr, result=None, exception=None):
    result = snapshot_arg(result)
    exception = snapshot_arg(exception)
    try:
        result_value = eval(expr)
        assert result_value == result
        assert exception == None  # (1)!
    except Exception as e:
        assert str(e) == exception
        assert result == None  # (2)!


def test_numbers():
    eval_expr("1+1")
    eval_expr("1/0")
```

1. Comparing the snapshot here ensures it gets reset if you change `expr` so that it no longer raises an exception.

2. Comparing the snapshot here ensures it gets reset if you change `expr` so that it no longer returns a value.

inline-snapshot only adds arguments whose value differs from the default.

<!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
``` python hl_lines="17 18"
from inline_snapshot import snapshot_arg


def eval_expr(expr, result=None, exception=None):
    result = snapshot_arg(result)
    exception = snapshot_arg(exception)
    try:
        result_value = eval(expr)
        assert result_value == result
        assert exception == None
    except Exception as e:
        assert str(e) == exception
        assert result == None


def test_numbers():
    eval_expr("1+1", result=2)
    eval_expr("1/0", exception="division by zero")
```



!!! info "Limitation"
    The default value can only be a value that can be evaluated with [ast.literal_eval][].


Snapshots created by `snapshot_arg()` follow the same rules as those created by `snapshot()`. You can use all the same operators such as [`<=`](cmp_snapshot.md) and [`in`](in_snapshot.md), and create sub-snapshots with [`[]`](getitem_snapshot.md).

You can also pass a `snapshot()` directly as the argument, just the same way you can nest snapshots.
This allows the The functions in `inline_snapshot.extra` are ported to `snapshot_arg()`

<!-- inline-snapshot: first_block outcome-failed=1 outcome-errors=1 -->
``` python
from inline_snapshot import snapshot
from inline_snapshot.extra import prints


def test_prints():
    with prints():
        print("hello")

    with prints(snapshot()):
        print("world")
```

<!-- inline-snapshot: create outcome-failed=1 outcome-errors=1 -->
``` python hl_lines="6"
from inline_snapshot import snapshot
from inline_snapshot.extra import prints


def test_prints():
    with prints(stdout="hello\n"):
        print("hello")

    with prints(snapshot()):
        print("world")
```

`snapshot_arg()` is in fact so general that you can re-implement `snapshot()` itself with it:

``` python
def snapshot(arg=...):
    return snapshot_arg(arg)
```
