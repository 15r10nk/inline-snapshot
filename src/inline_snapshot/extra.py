"""The following functions are build on top of inline-snapshot and could also
be implemented in an extra library.

They are part of inline-snapshot because they are general useful and do
not depend on other libraries.
"""

...  # prevent lint error with black and reorder-python-imports
import contextlib
from inline_snapshot._types import Snapshot


@contextlib.contextmanager
def raises(exception: Snapshot[str]):
    """Check that an exception is raised.

    Parameters:
        exception: snapshot which is compared with `#!python f"{type}: {message}"` if an exception occured or `#!python "<no exception>"` if no exception was raised.

    === "original"

        <!-- inline-snapshot: outcome-passed=1 outcome-errors=1 -->
        ```python
        from inline_snapshot import snapshot
        from inline_snapshot.extra import raises


        def test_raises():
            with raises(snapshot()):
                1 / 0
        ```

    === "--inline-snapshot=create"

        <!-- inline-snapshot: create outcome-passed=1 -->
        ```python
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
