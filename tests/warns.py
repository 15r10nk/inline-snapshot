import contextlib
import warnings


@contextlib.contextmanager
def warns(expected_warnings=[], include_line=False, include_file=False):
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
