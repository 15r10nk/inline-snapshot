import contextlib

from inline_snapshot._rewrite_code import ChangeRecorder
from inline_snapshot.extra import transformation


@contextlib.contextmanager
def apply_changes():
    recorder = ChangeRecorder()
    yield recorder

    recorder.fix_all()


@transformation
def path_transform(text):
    return text.replace("\\", "/")


class Store:
    def __eq__(self, other):
        self.value = other
        return True
