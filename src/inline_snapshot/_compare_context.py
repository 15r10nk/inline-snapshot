from contextlib import contextmanager


def compare_only():
    return _eq_check_only


_eq_check_only = False


@contextmanager
def compare_context():
    global _eq_check_only
    old_eq_only = _eq_check_only
    _eq_check_only = True
    yield
    _eq_check_only = old_eq_only
