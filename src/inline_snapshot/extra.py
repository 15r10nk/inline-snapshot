"""The following functions are build on top of inline-snapshot and could also
be implemented in an extra library.

They are part of inline-snapshot because they are general useful and do
not depend on other libraries.
"""

...  # prevent lint error with black and reorder-python-imports
import contextlib
from inline_snapshot._types import Snapshot
from contextlib import redirect_stdout, redirect_stderr
import io


@contextlib.contextmanager
def raises(exception: Snapshot[str]):
    """Check that an exception is raised.

    Parameters:
        exception: snapshot which is compared with `#!python f"{type}: {message}"` if an exception occured or `#!python "<no exception>"` if no exception was raised.

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

        <!-- inline-snapshot: create outcome-passed=1 -->
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

        <!-- inline-snapshot: create outcome-passed=1 -->
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
        ``` python hl_lines="3 9"
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
