# `inline_snapshot.extra`

The following functions are built on top of inline-snapshot and could also be implemented in an extra library. The source is added to the documentation, which allows you to look at how they are implemented and implement similar functions if you need them.

They are part of inline-snapshot because they are generally useful and do not depend on other libraries.

## `Transformed`

`Transformed` allows you to move transformations of your values from one side of the `==` to the other.

```
from inline_snapshot import snapshot
from inline_snapshot.extra import Transformed


def test_transform():
    numbers = [1, 8, 3, 7, 5]
    assert sorted(numbers) == snapshot()
    assert numbers == Transformed(sorted, snapshot())
```

Both assertions create the same snapshots.

```
from inline_snapshot import snapshot
from inline_snapshot.extra import Transformed


def test_transform():
    numbers = [1, 8, 3, 7, 5]
    assert sorted(numbers) == snapshot([1, 3, 5, 7, 8])
    assert numbers == Transformed(sorted, snapshot([1, 3, 5, 7, 8]))
```

`Transformed` is more flexible to use because you can also use it deep inside data structures. The following example shows how `Transformed` is used inside a dictionary.

```
from random import shuffle
from inline_snapshot import snapshot
from inline_snapshot.extra import Transformed


def request():
    data = [1, 8, 18748, 493]
    shuffle(data)
    return {"name": "example", "data": data}


def test_request():
    assert request() == snapshot(
        {
            "name": "example",
            "data": Transformed(sorted, snapshot([1, 8, 493, 18748])),
        }
    )
```

Or to normalize strings.

```
import re
from inline_snapshot import snapshot
from inline_snapshot.extra import Transformed


class Thing:
    def __repr__(self):
        return "<Thing with some random id 152897513>"


def without_ids(text):
    return re.sub(r"<([^0-9]*)[^>]+>", lambda m: f"<{m[1]} ...>", text)


def test_text_with_objects():
    text = f"text can contain {Thing()}"

    assert {"logs": text} == snapshot(
        {
            "logs": Transformed(
                without_ids,
                snapshot("text can contain <Thing with some random id  ...>"),
            )
        }
    )
```

Tip

You can use @transformation if you want to use the same transformation multiple times.

Source code in `src/inline_snapshot/extra.py`

````
@declare_unmanaged
class Transformed:
    """
    `Transformed` allows you to move transformations of your values from one side of the `==` to the other.

    <!-- inline-snapshot: first_block outcome-passed=1 outcome-errors=1 -->
    ``` python
    from inline_snapshot import snapshot
    from inline_snapshot.extra import Transformed


    def test_transform():
        numbers = [1, 8, 3, 7, 5]
        assert sorted(numbers) == snapshot()
        assert numbers == Transformed(sorted, snapshot())
    ```

    Both assertions create the same snapshots.

    <!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
    ``` python hl_lines="7 8"
    from inline_snapshot import snapshot
    from inline_snapshot.extra import Transformed


    def test_transform():
        numbers = [1, 8, 3, 7, 5]
        assert sorted(numbers) == snapshot([1, 3, 5, 7, 8])
        assert numbers == Transformed(sorted, snapshot([1, 3, 5, 7, 8]))
    ```

    `Transformed` is more flexible to use because you can also use it deep inside data structures.
    The following example shows how `Transformed` is used inside a dictionary.

    <!-- inline-snapshot: create fix first_block outcome-passed=1 -->
    ``` python
    from random import shuffle
    from inline_snapshot import snapshot
    from inline_snapshot.extra import Transformed


    def request():
        data = [1, 8, 18748, 493]
        shuffle(data)
        return {"name": "example", "data": data}


    def test_request():
        assert request() == snapshot(
            {
                "name": "example",
                "data": Transformed(sorted, snapshot([1, 8, 493, 18748])),
            }
        )
    ```

    Or to normalize strings.

    <!-- inline-snapshot: create fix first_block outcome-passed=1 -->
    ``` python
    import re
    from inline_snapshot import snapshot
    from inline_snapshot.extra import Transformed


    class Thing:
        def __repr__(self):
            return "<Thing with some random id 152897513>"


    def without_ids(text):
        return re.sub(r"<([^0-9]*)[^>]+>", lambda m: f"<{m[1]} ...>", text)


    def test_text_with_objects():
        text = f"text can contain {Thing()}"

        assert {"logs": text} == snapshot(
            {
                "logs": Transformed(
                    without_ids,
                    snapshot("text can contain <Thing with some random id  ...>"),
                )
            }
        )
    ```


    !!! Tip
        You can use [@transformation][inline_snapshot.extra.transformation] if you want to use the same transformation multiple times.
    """

    def __init__(
        self,
        func: Callable[[Any], Any],
        value: SnapshotArg = ...,
        should_be: Any = None,
    ) -> None:
        """
        Arguments:
            func: functions which is used to transform the value which is compared.
            value: the result of the transformation
            should_be: this argument is unused and only reported in the `repr()` to show you the last transformed value.
        """
        self._func = func
        self._value = snapshot_arg(value)
        self._last_transformed_value = None

    def __eq__(self, other) -> bool:
        self._last_transformed_value = self._func(other)
        return self._last_transformed_value == self._value

    def __repr__(self):
        try:
            code = code_repr(self._func)
        except Exception as e:  # pragma: no cover
            code = f"<exception {e}>"

        if self._last_transformed_value == self._value:
            return f"Transformed({code}, {self._value})"
        else:
            return f"Transformed({code}, {self._value}, should_be={self._last_transformed_value!r})"
````

### `__init__(func, value=..., should_be=None)`

Parameters:

| Name        | Type                   | Description                                                                                     | Default    |
| ----------- | ---------------------- | ----------------------------------------------------------------------------------------------- | ---------- |
| `func`      | `Callable[[Any], Any]` | functions which is used to transform the value which is compared.                               | *required* |
| `value`     | `SnapshotArg`          | the result of the transformation                                                                | `...`      |
| `should_be` | `Any`                  | this argument is unused and only reported in the repr() to show you the last transformed value. | `None`     |

Source code in `src/inline_snapshot/extra.py`

```
def __init__(
    self,
    func: Callable[[Any], Any],
    value: SnapshotArg = ...,
    should_be: Any = None,
) -> None:
    """
    Arguments:
        func: functions which is used to transform the value which is compared.
        value: the result of the transformation
        should_be: this argument is unused and only reported in the `repr()` to show you the last transformed value.
    """
    self._func = func
    self._value = snapshot_arg(value)
    self._last_transformed_value = None
```

## `prints(*, stdout='', stderr='')`

Uses `contextlib.redirect_stderr/stdout` to capture the output and compare it with the snapshots. `dirty_equals.IsStr` can be used to ignore the output if needed.

Parameters:

| Name     | Type               | Description                                             | Default |
| -------- | ------------------ | ------------------------------------------------------- | ------- |
| `stdout` | `SnapshotArg[str]` | Snapshot that is compared to the recorded output.       | `''`    |
| `stderr` | `SnapshotArg[str]` | Snapshot that is compared to the recorded error output. | `''`    |

```
import sys
from inline_snapshot import snapshot
from inline_snapshot.extra import prints


def test_prints():
    with prints():
        print("hello world")
        print("some error", file=sys.stderr)
```

```
import sys
from inline_snapshot import snapshot
from inline_snapshot.extra import prints


def test_prints():
    with prints(stderr="some error\n", stdout="hello world\n"):
        print("hello world")
        print("some error", file=sys.stderr)
```

```
import sys
from dirty_equals import IsStr
from inline_snapshot import snapshot
from inline_snapshot.extra import prints


def test_prints():
    with prints(
        stdout=IsStr(),
        stderr="some error\n",
    ):
        print("hello world")
        print("some error", file=sys.stderr)
```

Limitation: CPython < 3.11

You have to use `snapshot(...)` as argument when you want to fix values on CPython < 3.11.

```
def test_prints():
    with prints(stdout=snapshot()):
        print("hello")
```

Source code in `src/inline_snapshot/extra.py`

````
@contextlib.contextmanager
def prints(*, stdout: SnapshotArg[str] = "", stderr: SnapshotArg[str] = ""):
    """Uses `contextlib.redirect_stderr/stdout` to capture the output and
    compare it with the snapshots. `dirty_equals.IsStr` can be used to ignore
    the output if needed.

    Parameters:
        stdout: Snapshot that is compared to the recorded output.
        stderr: Snapshot that is compared to the recorded error output.

    === "original"

        <!-- inline-snapshot: first_block outcome-failed=1 outcome-errors=1 -->
        ``` python
        import sys
        from inline_snapshot import snapshot
        from inline_snapshot.extra import prints


        def test_prints():
            with prints():
                print("hello world")
                print("some error", file=sys.stderr)
        ```

    === "--inline-snapshot=create"

        <!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
        ``` python hl_lines="7"
        import sys
        from inline_snapshot import snapshot
        from inline_snapshot.extra import prints


        def test_prints():
            with prints(stderr="some error\\n", stdout="hello world\\n"):
                print("hello world")
                print("some error", file=sys.stderr)
        ```

    === "ignore stdout"

        <!-- inline-snapshot: outcome-passed=1 -->
        ``` python hl_lines="2 8 9 10 11"
        import sys
        from dirty_equals import IsStr
        from inline_snapshot import snapshot
        from inline_snapshot.extra import prints


        def test_prints():
            with prints(
                stdout=IsStr(),
                stderr="some error\\n",
            ):
                print("hello world")
                print("some error", file=sys.stderr)
        ```

    ??? info "Limitation: CPython < 3.11"
        You have to use `snapshot(...)` as argument when you want to fix values on CPython < 3.11.
        ``` python
        def test_prints():
            with prints(stdout=snapshot()):
                print("hello")
        ```
    """

    with redirect_stdout(io.StringIO()) as stdout_io:
        with redirect_stderr(io.StringIO()) as stderr_io:
            yield

    assert stderr_io.getvalue() == snapshot_arg(stderr)
    assert stdout_io.getvalue() == snapshot_arg(stdout)
````

## `raises(exception=...)`

Check that an exception is raised.

Parameters:

| Name        | Type               | Description                                                                                                                                                                                                                                                                                          | Default |
| ----------- | ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `exception` | `SnapshotArg[str]` | Snapshot that is compared with the formatted exception if an exception occurs: type(exception).__name__ when the message is empty or whitespace only, f"{type}:\\n{message}" when the message contains a newline, and f"{type}: {message}" otherwise; or "<no exception>" if no exception is raised. | `...`   |

```
from inline_snapshot import snapshot
from inline_snapshot.extra import raises


def test_raises():
    with raises():
        1 / 0
```

```
from inline_snapshot import snapshot
from inline_snapshot.extra import raises


def test_raises():
    with raises("ZeroDivisionError: division by zero"):
        1 / 0
```

Limitation: CPython < 3.11

You have to use `snapshot(...)` as argument when you want to fix values on CPython < 3.11.

```
def test_raises():
    with raises(snapshot()):
        1 / 0
```

Source code in `src/inline_snapshot/extra.py`

````
@contextlib.contextmanager
def raises(exception: SnapshotArg[str] = ..., /):
    """Check that an exception is raised.

    Parameters:
        exception: Snapshot that is compared with the formatted exception if an exception occurs:
            `#!python type(exception).__name__` when the message is empty or whitespace only,
            `#!python f"{type}:\\n{message}"` when the message contains a newline, and
            `#!python f"{type}: {message}"` otherwise;
            or `#!python "<no exception>"` if no exception is raised.


    === "original"

        <!-- inline-snapshot: first_block outcome-passed=1 outcome-errors=1 -->
        ``` python
        from inline_snapshot import snapshot
        from inline_snapshot.extra import raises


        def test_raises():
            with raises():
                1 / 0
        ```

    === "--inline-snapshot=create"

        <!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
        ``` python hl_lines="6"
        from inline_snapshot import snapshot
        from inline_snapshot.extra import raises


        def test_raises():
            with raises("ZeroDivisionError: division by zero"):
                1 / 0
        ```

    ??? info "Limitation: CPython < 3.11"
        You have to use `snapshot(...)` as argument when you want to fix values on CPython < 3.11.
        ``` python
        def test_raises():
            with raises(snapshot()):
                1 / 0
        ```
    """
    exception = snapshot_arg(exception)

    try:
        yield
    except BaseException as ex:
        assert _format_exception(ex) == exception
    else:
        assert "<no exception>" == exception
````

## `transformation(func)`

`@transformation` can be used to bind a function to Transformed, which simplifies your code if you want to use the same transformation multiple times.

```
import re
from inline_snapshot import snapshot
from inline_snapshot.extra import transformation


class Thing:
    def __repr__(self):
        return "<Thing with some random id 152897513>"


@transformation
def WithoutIds(text):
    return re.sub(r"<([^0-9]*)[^>]+>", lambda m: f"<{m[1]} ...>", text)


def test_text_with_objects():
    text = f"text can contain {Thing()}"

    assert {"logs": [text]} == snapshot(
        {
            "logs": [
                WithoutIds(
                    snapshot(
                        "text can contain <Thing with some random id  ...>"
                    )
                )
            ]
        }
    )
```

Tip

The argument of `WithoutIds` can also be an external `WithoutIds(external())` if you want to store a large log in an external file.

Source code in `src/inline_snapshot/extra.py`

````
def transformation(func):
    """

    `@transformation` can be used to bind a function to [Transformed][inline_snapshot.extra.Transformed],
    which simplifies your code if you want to use the same transformation multiple times.

    <!-- inline-snapshot: create first_block outcome-passed=1 -->
    ``` python
    import re
    from inline_snapshot import snapshot
    from inline_snapshot.extra import transformation


    class Thing:
        def __repr__(self):
            return "<Thing with some random id 152897513>"


    @transformation
    def WithoutIds(text):
        return re.sub(r"<([^0-9]*)[^>]+>", lambda m: f"<{m[1]} ...>", text)


    def test_text_with_objects():
        text = f"text can contain {Thing()}"

        assert {"logs": [text]} == snapshot(
            {
                "logs": [
                    WithoutIds(
                        snapshot(
                            "text can contain <Thing with some random id  ...>"
                        )
                    )
                ]
            }
        )
    ```

    !!! Tip
        The argument of `WithoutIds` can also be an external `WithoutIds(external())` if you want to store a large log in an external file.
    """

    def f(value):
        return Transformed(func, snapshot_arg(value))

    return f
````

## `warns(expected_warnings=..., /, include_line=False, include_file=False)`

Captures warnings with `warnings.catch_warnings` and compares them against expected warnings.

Parameters:

| Name                | Type                         | Description                                                       | Default |
| ------------------- | ---------------------------- | ----------------------------------------------------------------- | ------- |
| `expected_warnings` | `SnapshotArg[List[Warning]]` | Snapshot containing a list of expected warnings.                  | `...`   |
| `include_line`      | `bool`                       | If True, each expected warning is a tuple (line_number, message). | `False` |
| `include_file`      | `bool`                       | If True, each expected warning is a tuple (filename, message).    | `False` |

The format of the expected warning:

- `(filename, line_number, message)` if both `include_line` and `include_file` are `True`.
- `(line_number, message)` if only `include_line` is `True`.
- `(filename, message)` if only `include_file` is `True`.
- A string `message` if both are `False`.

```
from warnings import warn
from inline_snapshot import snapshot
from inline_snapshot.extra import warns


def test_warns():
    with warns(include_line=True):
        warn("some problem")
```

```
from warnings import warn
from inline_snapshot import snapshot
from inline_snapshot.extra import warns


def test_warns():
    with warns([(8, "UserWarning: some problem")], include_line=True):
        warn("some problem")
```

Limitation: CPython < 3.11

You have to use `snapshot(...)` as argument when you want to fix values on CPython < 3.11.

```
def test_warns():
    with warns(snapshot()):
        warn("some problem")
```

Source code in `src/inline_snapshot/extra.py`

````
@contextlib.contextmanager
def warns(
    expected_warnings: SnapshotArg[List[Warning]] = ...,
    /,
    include_line: bool = False,
    include_file: bool = False,
):
    """
    Captures warnings with `warnings.catch_warnings` and compares them against expected warnings.

    Parameters:
        expected_warnings: Snapshot containing a list of expected warnings.
        include_line: If `True`, each expected warning is a tuple `(line_number, message)`.
        include_file: If `True`, each expected warning is a tuple `(filename, message)`.

    The format of the expected warning:

    - `(filename, line_number, message)` if both `include_line` and `include_file` are `True`.
    - `(line_number, message)` if only `include_line` is `True`.
    - `(filename, message)` if only `include_file` is `True`.
    - A string `message` if both are `False`.

    === "original"

        <!-- inline-snapshot: first_block outcome-passed=1 outcome-errors=1 -->
        ``` python
        from warnings import warn
        from inline_snapshot import snapshot
        from inline_snapshot.extra import warns


        def test_warns():
            with warns(include_line=True):
                warn("some problem")
        ```

    === "--inline-snapshot=create"

        <!-- inline-snapshot: create fix outcome-passed=1 -->
        ``` python hl_lines="7"
        from warnings import warn
        from inline_snapshot import snapshot
        from inline_snapshot.extra import warns


        def test_warns():
            with warns([(8, "UserWarning: some problem")], include_line=True):
                warn("some problem")
        ```

    ??? info "Limitation: CPython < 3.11"
        You have to use `snapshot(...)` as argument when you want to fix values on CPython < 3.11.
        ``` python
        def test_warns():
            with warns(snapshot()):
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

    assert [make_warning(w) for w in result] == snapshot_arg(expected_warnings)
````
