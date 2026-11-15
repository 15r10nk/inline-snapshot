from io import StringIO

import pytest
from rich.console import Console

from inline_snapshot._core._global_state import snapshot_env
from inline_snapshot._core._snapshot_session import SnapshotSession
from inline_snapshot.plugin import Storage
from inline_snapshot.plugin import hookimpl


@pytest.mark.parametrize("trim_requested", [False, True])
@pytest.mark.parametrize("trim_allowed", [False, True])
def test_enumerate_only_when_trimming(tmp_path, trim_requested, trim_allowed):
    calls = []

    class CustomStorage(Storage):
        def find_unused_externals(self, used_externals):
            calls.append("enumerate")
            return []

        def check_externals(self, used_externals):
            calls.append("check")

    class CustomPlugin:
        @hookimpl
        def register_storages(self):
            return {"custom": CustomStorage()}

    with snapshot_env() as state:
        state.config.storage_dir = tmp_path
        state.pm.register(CustomPlugin())
        session = SnapshotSession()
        session.load_config(
            pyproject=None,
            cli_flags={"trim"} if trim_requested else set(),
            parallel_run=False,
            error=pytest.fail,
            project_root=tmp_path,
        )
        session.show_report(Console(file=StringIO()), trim_allowed=trim_allowed)

    assert calls == (
        ["enumerate", "check"] if trim_requested and trim_allowed else ["check"]
    )
