import contextlib

from inline_snapshot._rewrite_code import ChangeRecorder


@contextlib.contextmanager
def apply_changes():
    recorder = ChangeRecorder()
    yield recorder

    recorder.fix_all()
