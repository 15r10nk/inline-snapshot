import pytest

from inline_snapshot._core._exceptions import UsageError
from inline_snapshot._core._global_state import snapshot_env
from inline_snapshot._core._snapshot_session import SnapshotSession
from inline_snapshot.plugin import Storage
from inline_snapshot.plugin import hookimpl
from inline_snapshot.testing import Example


@pytest.mark.parametrize("conftest_dir", ["", "tests/"])
def test_register_storages(conftest_dir):
    Example(
        {
            "pyproject.toml": '[tool.inline-snapshot]\nstorage-dir="custom-storage"',
            f"{conftest_dir}conftest.py": """\
from pathlib import Path

from inline_snapshot.plugin import Storage, hookimpl

class CustomStorage(Storage):
    def find_unused_externals(self, used_externals):
        return []

    def check_externals(self, used_externals):
        pass

@hookimpl
def register_storages(storage_dir):
    assert storage_dir == Path("custom-storage").resolve()
    return {"custom": CustomStorage()}
""",
            "tests/test_something.py": """\
from pathlib import Path
from inline_snapshot.plugin import ExternalLocation, Storage
from inline_snapshot._core._global_state import state

def test_registered():
    assert set(state().all_storages) == {"hash", "uuid", "custom"}
    assert isinstance(state().all_storages["custom"], Storage)
    assert state().all_storages["hash"].directory == Path("custom-storage").resolve() / "external"
    assert ExternalLocation.from_name("custom:value.txt").storage == "custom"
""",
        }
    ).run_inline(changed_files={}).run_pytest(outcomes={"passed": 1}, changed_files={})


@pytest.mark.parametrize("name", ["hash", "uuid", "custom"])
def test_duplicate_storage_name(name):
    example = duplicate_example(name)
    with pytest.raises(UsageError, match=f"storage '{name}' is already registered"):
        example.run_inline()


def duplicate_example(name):
    return Example(
        {
            "conftest.py": f"""\
from inline_snapshot.plugin import Storage, hookimpl

class CustomStorage(Storage):
    def find_unused_externals(self, used_externals):
        return []

    def check_externals(self, used_externals):
        pass

class InlineSnapshotFirstPlugin:
    @hookimpl
    def register_storages(self):
        return {{"{name}": CustomStorage()}}

class InlineSnapshotSecondPlugin:
    @hookimpl
    def register_storages(self):
        return {{"{name}": CustomStorage()}}
""",
            "tests/test_something.py": "def test_something(): pass",
        }
    )


@pytest.mark.parametrize("name", ["hash", "uuid"])
@pytest.mark.parametrize("tryfirst", [False, True])
def test_builtin_storage_name_is_reserved(tmp_path, name, tryfirst):
    class CustomPlugin:
        @hookimpl(tryfirst=tryfirst, trylast=not tryfirst)
        def register_storages(self):
            return {name: Storage()}

    with snapshot_env() as state:
        state.config.storage_dir = tmp_path
        state.pm.register(CustomPlugin())
        with pytest.raises(UsageError, match=f"storage '{name}' is already registered"):
            SnapshotSession().load_config(
                pyproject=None,
                cli_flags=set(),
                parallel_run=False,
                error=pytest.fail,
                project_root=tmp_path,
            )


@pytest.mark.parametrize(
    "name",
    ["", "bad:name", "with space", "with-hyphen", "with_underscore", "abc1", "ä", 1],
)
def test_invalid_storage_name(tmp_path, name):
    class CustomPlugin:
        @hookimpl
        def register_storages(self):
            return {name: Storage()}

    with snapshot_env() as state:
        state.config.storage_dir = tmp_path
        state.pm.register(CustomPlugin())
        with pytest.raises(
            UsageError, match="storage names must contain only ASCII letters"
        ):
            SnapshotSession().load_config(
                pyproject=None,
                cli_flags=set(),
                parallel_run=False,
                error=pytest.fail,
                project_root=tmp_path,
            )


def test_storage_name_with_uppercase_letters(tmp_path):
    class CustomPlugin:
        @hookimpl
        def register_storages(self):
            return {"Custom": Storage()}

    with snapshot_env() as state:
        state.config.storage_dir = tmp_path
        state.pm.register(CustomPlugin())
        SnapshotSession().load_config(
            pyproject=None,
            cli_flags=set(),
            parallel_run=False,
            error=pytest.fail,
            project_root=tmp_path,
        )
        assert isinstance(state.all_storages["Custom"], Storage)
