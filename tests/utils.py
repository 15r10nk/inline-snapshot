import contextlib
from contextlib import contextmanager

import pytest

import inline_snapshot._config as _config
import inline_snapshot._external as external
from inline_snapshot._global_state import state
from inline_snapshot._rewrite_code import ChangeRecorder
from inline_snapshot.testing._example import snapshot_env

__all__ = ("snapshot_env",)


@contextlib.contextmanager
def config(**args):
    current_config = _config.config
    _config.config = _config.Config(**args)
    try:
        yield
    finally:
        _config.config = current_config


@contextlib.contextmanager
def apply_changes():
    recorder = ChangeRecorder()
    yield recorder

    recorder.fix_all()


@contextmanager
def useStorage(storage):
    old_storage = state().storage
    state().storage = storage
    yield
    state().storage = old_storage


@pytest.fixture()
def storage(tmp_path):
    storage = external.DiscStorage(tmp_path / ".storage")
    with useStorage(storage):
        yield storage
