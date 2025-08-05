"""The following functions are built on top of inline-snapshot and could also
be implemented in an extra library.
The source is added to the documentation, which allows you to look at how they are implemented and implement similar functions if you need them.

They are part of inline-snapshot because they are generally useful and do
not depend on other libraries.
"""

import contextlib
import io
import warnings
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from typing import Any
from typing import Callable
from typing import List
from typing import Tuple
from typing import Union

from inline_snapshot._code_repr import code_repr

from ._types import Snapshot
from ._unmanaged import declare_unmanaged


@contextlib.contextmanager
def raises(exception: Snapshot[str]):
    """Check that an exception is raised.

    Parameters:
        exception: Snapshot that is compared with `#!python f"{type}: {message}"` if an exception occurs, or `#!python "<no exception>"` if no exception is raised.

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


@contextlib.contextmanager
def prints(*, stdout: Snapshot[str] = "", stderr: Snapshot[str] = ""):
    """Uses `contextlib.redirect_stderr/stdout` to capture the output and
    compare it with the snapshots. `dirty_equals.IsStr` can be used to ignore
    the output if needed.

    Parameters:
        stdout: Snapshot that is compared to the recorded output.
        stderr: Snapshot that is compared to the recorded error output.

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


Warning = Union[str, Tuple[int, str], Tuple[str, str], Tuple[str, int, str]]


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
    from inline_snapshot.extra import Transformed
    from inline_snapshot import snapshot
    import re


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
        self, func: Callable[[Any], Any], value: Snapshot, should_be: Any = None
    ) -> None:
        """
        Arguments:
            func: functions which is used to transform the value which is compared.
            value: the result of the transformation
            should_be: this argument is unused and only reported in the `repr()` to show you the last transformed value.
        """
        self._func = func
        self._value = value
        self._last_transformed_value = None

    def __eq__(self, other) -> bool:
        self._last_transformed_value = self._func(other)
        return self._last_transformed_value == self._value

    def __repr__(self):
        if self._last_transformed_value == self._value:
            return f"Transformed({code_repr(self._func)}, {self._value})"
        else:
            return f"Transformed({code_repr(self._func)}, {self._value}, should_be={self._last_transformed_value!r})"


def transformation(func):
    """

    `@transformation` can be used to bind a function to [Transformed][inline_snapshot.extra.Transformed],
    which simplifies your code if you want to use the same transformation multiple times.

    <!-- inline-snapshot: create first_block outcome-passed=1 -->
    ``` python
    from inline_snapshot.extra import transformation
    from inline_snapshot import snapshot
    import re


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
        return Transformed(func, value)

    return f
