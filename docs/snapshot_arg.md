
# snapshot_arg(...)

`snapshot_arg` lets you embed snapshot assertions inside a helper function, so callers don't need to pass `snapshot()` at every call site.
It is an advanced feature for integrating inline-snapshot more deeply into your tests or an existing testing framework.

Consider a helper like this, where callers must pass `snapshot()` explicitly:

``` python
from inline_snapshot import snapshot


def check(data, min_value, max_value):
    assert min(data) == min_value
    assert max(data) == max_value


def test():
    check([1, 3], snapshot(), snapshot())
    check([5, 5], snapshot(), snapshot())
```

With `snapshot_arg` you can move the snapshot call into `check` itself, eliminating the repetition at every call site.
Snapshots created by `snapshot_arg()` follow the same rules as those created by `snapshot()`. You can use all the same operators such as [`<=`](cmp_snapshot.md) and [`in`](in_snapshot.md), and create sub-snapshots with [`[]`](getitem_snapshot.md).

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
The `...` acts as a placeholder default, so callers don't need to pass a value — inline-snapshot fills one in when you run `pytest`.

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

`snapshot_arg` also supports real default values: inline-snapshot omits an argument at the call site when its current value matches the default.

A default of `...` uses the [*create*](categories.md#create) category to generate the initial value. Any other default uses [*fix*](categories.md#fix), and the argument is only written if the actual value differs from that default.

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

1. Asserting this snapshot ensures it gets reset when `expr` stops raising an exception.

2. Asserting this snapshot ensures it gets reset when `expr` stops returning a value.

We are using `None` as the default because we want to omit the argument when its value matches the default. Using `...` would force inline-snapshot to always create it.
Running with `--inline-snapshot=create` fills in only the arguments whose value differs from the default:

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
    The default value must be a literal that can be evaluated with [ast.literal_eval][].


## Backward compatibility

You can pass a `snapshot()` directly as the argument, just as you can [nest snapshots](eq_snapshot.md#inner-snapshots).
This means that any place where you previously passed `snapshot()` explicitly continues to work.
The functions in `inline_snapshot.extra` now use `snapshot_arg()` internally, so they accept both styles.

<!-- inline-snapshot: first_block outcome-failed=1 outcome-errors=1 -->
``` python
from inline_snapshot import snapshot
from inline_snapshot.extra import prints


def test_prints():
    with prints():  # (1)!
        print("hello")

    with prints(snapshot()):  # (2)!
        print("world")
```

1. New style — no `snapshot()` needed.
2. Old style — `snapshot()` is now redundant and can be removed.

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

## Where can I use it?

`snapshot_arg()` can be used in the following contexts:

=== "functions"
    <!-- inline-snapshot: create fix first_block outcome-passed=1 -->
    ``` python
    from inline_snapshot import snapshot_arg


    def check(input, output=...):
        assert input.lower() == snapshot_arg(output)


    def test_check():
        check("Hello", output="hello")
    ```
=== "methods"
    <!-- inline-snapshot: create fix first_block outcome-passed=1 -->
    ``` python
    from inline_snapshot import snapshot_arg


    class Checker:
        def check(self, input, output=...):
            assert input.lower() == snapshot_arg(output)


    def test_check():
        Checker().check("Hello", output="hello")
    ```
=== "constructors"
    <!-- inline-snapshot: create fix first_block outcome-passed=1 -->
    ``` python
    from inline_snapshot import snapshot_arg


    class Checker:
        def __init__(self, output=...):
            self.output = snapshot_arg(output)

        def check(self, input, output=...):
            assert input.lower() == self.output


    def test_check():
        Checker(output="hello").check("Hello")
    ```

=== "context managers"
    <!-- inline-snapshot: create fix first_block outcome-passed=1 -->
    ``` python
    from contextlib import contextmanager
    from inline_snapshot import snapshot_arg


    @contextmanager
    def make_checker(output=...):
        output = snapshot_arg(output)

        def check(input):
            assert input.lower() == output

        yield check


    def test_check():
        with make_checker("hello") as check:
            check("Hello")
    ```

    !!! info "Limitation"
        It is not possible to use context managers with `snapshot_arg()` on CPython < 3.11.

        It is also not possible to use decorators other than `contextmanager` that wrap the function inside another function.


## Difference from `snapshot()`

`snapshot_arg()` is general enough that `snapshot()` itself can be re-implemented with it:

``` python
def snapshot(arg=...):
    return snapshot_arg(arg)
```

The only difference is that `snapshot_arg()` is slightly slower, because it needs to inspect the calling and called function of your code. This is not a problem when you use `--inline-snapshot=disable` (the default in CI), because `snapshot_arg(x)` is a no-op in this case and simply returns `x`.
