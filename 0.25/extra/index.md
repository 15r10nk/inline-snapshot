# `inline_snapshot.extra`

The following functions are build on top of inline-snapshot and could also be implemented in an extra library.

They are part of inline-snapshot because they are general useful and do not depend on other libraries.

## `prints(*, stdout='', stderr='')`

Uses `contextlib.redirect_stderr/stdout` to capture the output and compare it with the snapshots. `dirty_equals.IsStr` can be used to ignore the output if needed.

Parameters:

| Name     | Type            | Description                                             | Default |
| -------- | --------------- | ------------------------------------------------------- | ------- |
| `stdout` | `Snapshot[str]` | snapshot which is compared to the recorded output       | `''`    |
| `stderr` | `Snapshot[str]` | snapshot which is compared to the recorded error output | `''`    |

```
from inline_snapshot import snapshot
from inline_snapshot.extra import prints
import sys


def test_prints():
    with prints(stdout=snapshot(), stderr=snapshot()):
        print("hello world")
        print("some error", file=sys.stderr)

```

```
from inline_snapshot import snapshot
from inline_snapshot.extra import prints
import sys


def test_prints():
    with prints(
        stdout=snapshot("hello world\n"), stderr=snapshot("some error\n")
    ):
        print("hello world")
        print("some error", file=sys.stderr)

```

```
from inline_snapshot import snapshot
from inline_snapshot.extra import prints
from dirty_equals import IsStr
import sys


def test_prints():
    with prints(
        stdout=IsStr(),
        stderr=snapshot("some error\n"),
    ):
        print("hello world")
        print("some error", file=sys.stderr)

```

Source code in `src/inline_snapshot/extra.py`

````
@contextlib.contextmanager
def prints(*, stdout: Snapshot[str] = "", stderr: Snapshot[str] = ""):
    """Uses `contextlib.redirect_stderr/stdout` to capture the output and
    compare it with the snapshots. `dirty_equals.IsStr` can be used to ignore
    the output if needed.

    Parameters:
        stdout: snapshot which is compared to the recorded output
        stderr: snapshot which is compared to the recorded error output

    === "original"

        <!-- inline-snapshot: first_block outcome-passed=1 outcome-errors=1 -->
        ``` python
        from inline_snapshot import snapshot
        from inline_snapshot.extra import prints
        import sys


        def test_prints():
            with prints(stdout=snapshot(), stderr=snapshot()):
                print("hello world")
                print("some error", file=sys.stderr)
        ```

    === "--inline-snapshot=create"

        <!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
        ``` python hl_lines="7 8 9"
        from inline_snapshot import snapshot
        from inline_snapshot.extra import prints
        import sys


        def test_prints():
            with prints(
                stdout=snapshot("hello world\\n"), stderr=snapshot("some error\\n")
            ):
                print("hello world")
                print("some error", file=sys.stderr)
        ```

    === "ignore stdout"

        <!-- inline-snapshot: outcome-passed=1 -->
        ``` python hl_lines="3 9 10"
        from inline_snapshot import snapshot
        from inline_snapshot.extra import prints
        from dirty_equals import IsStr
        import sys


        def test_prints():
            with prints(
                stdout=IsStr(),
                stderr=snapshot("some error\\n"),
            ):
                print("hello world")
                print("some error", file=sys.stderr)
        ```
    """

    with redirect_stdout(io.StringIO()) as stdout_io:
        with redirect_stderr(io.StringIO()) as stderr_io:
            yield

    assert stderr_io.getvalue() == stderr
    assert stdout_io.getvalue() == stdout

````

## `raises(exception)`

Check that an exception is raised.

Parameters:

| Name        | Type            | Description                                                                                                                   | Default    |
| ----------- | --------------- | ----------------------------------------------------------------------------------------------------------------------------- | ---------- |
| `exception` | `Snapshot[str]` | snapshot which is compared with f"{type}: {message}" if an exception occurred or "<no exception>" if no exception was raised. | *required* |

```
from inline_snapshot import snapshot
from inline_snapshot.extra import raises


def test_raises():
    with raises(snapshot()):
        1 / 0

```

```
from inline_snapshot import snapshot
from inline_snapshot.extra import raises


def test_raises():
    with raises(snapshot("ZeroDivisionError: division by zero")):
        1 / 0

```

Source code in `src/inline_snapshot/extra.py`

````
@contextlib.contextmanager
def raises(exception: Snapshot[str]):
    """Check that an exception is raised.

    Parameters:
        exception: snapshot which is compared with `#!python f"{type}: {message}"` if an exception occurred or `#!python "<no exception>"` if no exception was raised.

    === "original"

        <!-- inline-snapshot: first_block outcome-passed=1 outcome-errors=1 -->
        ``` python
        from inline_snapshot import snapshot
        from inline_snapshot.extra import raises


        def test_raises():
            with raises(snapshot()):
                1 / 0
        ```

    === "--inline-snapshot=create"

        <!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
        ``` python hl_lines="6"
        from inline_snapshot import snapshot
        from inline_snapshot.extra import raises


        def test_raises():
            with raises(snapshot("ZeroDivisionError: division by zero")):
                1 / 0
        ```
    """

    try:
        yield
    except Exception as ex:
        msg = str(ex)
        if "\n" in msg:
            assert f"{type(ex).__name__}:\n{ex}" == exception
        else:
            assert f"{type(ex).__name__}: {ex}" == exception
    else:
        assert "<no exception>" == exception

````

## `warns(expected_warnings, /, include_line=False, include_file=False)`

Captures warnings with `warnings.catch_warnings` and compares them against expected warnings.

Parameters:

| Name                | Type                      | Description                                                      | Default    |
| ------------------- | ------------------------- | ---------------------------------------------------------------- | ---------- |
| `expected_warnings` | `Snapshot[List[Warning]]` | Snapshot containing a list of expected warnings.                 | *required* |
| `include_line`      | `bool`                    | If True, each expected warning is a tuple (linenumber, message). | `False`    |
| `include_file`      | `bool`                    | If True, each expected warning is a tuple (filename, message).   | `False`    |

The format of the expected warning:

- `(filename, linenumber, message)` if both `include_line` and `include_file` are `True`.
- `(linenumber, message)` if only `include_line` is `True`.
- `(filename, message)` if only `include_file` is `True`.
- A string `message` if both are `False`.

```
from inline_snapshot import snapshot
from inline_snapshot.extra import warns
from warnings import warn


def test_warns():
    with warns(snapshot(), include_line=True):
        warn("some problem")

```

```
from inline_snapshot import snapshot
from inline_snapshot.extra import warns
from warnings import warn


def test_warns():
    with warns(snapshot([(8, "UserWarning: some problem")]), include_line=True):
        warn("some problem")

```

Source code in `src/inline_snapshot/extra.py`

````
@contextlib.contextmanager
def warns(
    expected_warnings: Snapshot[List[Warning]],
    /,
    include_line: bool = False,
    include_file: bool = False,
):
    """
    Captures warnings with `warnings.catch_warnings` and compares them against expected warnings.

    Parameters:
        expected_warnings: Snapshot containing a list of expected warnings.
        include_line: If `True`, each expected warning is a tuple `(linenumber, message)`.
        include_file: If `True`, each expected warning is a tuple `(filename, message)`.

    The format of the expected warning:

    - `(filename, linenumber, message)` if both `include_line` and `include_file` are `True`.
    - `(linenumber, message)` if only `include_line` is `True`.
    - `(filename, message)` if only `include_file` is `True`.
    - A string `message` if both are `False`.

    === "original"

        <!-- inline-snapshot: first_block outcome-passed=1 outcome-errors=1 -->
        ``` python
        from inline_snapshot import snapshot
        from inline_snapshot.extra import warns
        from warnings import warn


        def test_warns():
            with warns(snapshot(), include_line=True):
                warn("some problem")
        ```

    === "--inline-snapshot=create"

        <!-- inline-snapshot: create fix outcome-passed=1 outcome-errors=1 -->
        ``` python hl_lines="7"
        from inline_snapshot import snapshot
        from inline_snapshot.extra import warns
        from warnings import warn


        def test_warns():
            with warns(snapshot([(8, "UserWarning: some problem")]), include_line=True):
                warn("some problem")
        ```
    """
    with warnings.catch_warnings(record=True) as result:
        warnings.simplefilter("always")
        yield

    def make_warning(w):
        message = f"{w.category.__name__}: {w.message}"
        if not include_line and not include_file:
            return message
        message = (message,)

        if include_line:
            message = (w.lineno, *message)
        if include_file:
            message = (w.filename, *message)

        return message

    assert [make_warning(w) for w in result] == expected_warnings

````
