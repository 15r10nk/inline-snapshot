import contextlib
from contextlib import contextmanager

import inline_snapshot._config as _config
import inline_snapshot._external as external
import inline_snapshot._inline_snapshot as inline_snapshot
import pytest
from inline_snapshot._rewrite_code import ChangeRecorder


@contextlib.contextmanager
def snapshot_env():
    current = (
        inline_snapshot.snapshots,
        inline_snapshot._update_flags,
        inline_snapshot._active,
        inline_snapshot.found_snapshots,
        external.storage,
        inline_snapshot._files_with_snapshots,
    )

    inline_snapshot.snapshots = {}
    inline_snapshot._update_flags = inline_snapshot.Flags()
    inline_snapshot._active = True
    inline_snapshot.found_snapshots = []
    external.storage = None
    inline_snapshot._files_with_snapshots = set()

    try:
        yield
    finally:
        (
            inline_snapshot.snapshots,
            inline_snapshot._update_flags,
            inline_snapshot._active,
            inline_snapshot.found_snapshots,
            external.storage,
            inline_snapshot._files_with_snapshots,
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

        recorder.fix_all(tags=["inline_snapshot"])


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
