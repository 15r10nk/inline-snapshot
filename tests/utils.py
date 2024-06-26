import contextlib
from contextlib import contextmanager

import pytest

import inline_snapshot._config as _config
import inline_snapshot._external as external
import inline_snapshot._inline_snapshot as inline_snapshot
from inline_snapshot._rewrite_code import ChangeRecorder


@contextlib.contextmanager
def snapshot_env():
    current = (
        inline_snapshot.snapshots,
        inline_snapshot._update_flags,
        inline_snapshot._active,
        external.storage,
        inline_snapshot._files_with_snapshots,
        inline_snapshot._missing_values,
    )

    inline_snapshot.snapshots = {}
    inline_snapshot._update_flags = inline_snapshot.Flags()
    inline_snapshot._active = True
    external.storage = None
    inline_snapshot._files_with_snapshots = set()
    inline_snapshot._missing_values = 0

    try:
        yield
    finally:
        (
            inline_snapshot.snapshots,
            inline_snapshot._update_flags,
            inline_snapshot._active,
            external.storage,
            inline_snapshot._files_with_snapshots,
            inline_snapshot._missing_values,
        ) = current


@contextlib.contextmanager
def config(**args):
    current_config = _config.config
    _config.config = _config.Config(**args)
    try:
        yield
    finally:
        _config.config = current_config


@contextlib.contextmanager
def raises(snapshot):
    with pytest.raises(Exception) as excinfo:
        yield

    assert f"{type(excinfo.value).__name__}: {excinfo.value}" == snapshot


@contextlib.contextmanager
def apply_changes():
    with ChangeRecorder().activate() as recorder:
        yield

        recorder.fix_all()


@contextmanager
def useStorage(storage):
    old_storage = external.storage
    external.storage = storage
    yield
    external.storage = old_storage


@pytest.fixture()
def storage(tmp_path):
    storage = external.DiscStorage(tmp_path / ".storage")
    with useStorage(storage):
        yield storage
