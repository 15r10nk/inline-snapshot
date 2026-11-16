import pytest
from dirty_equals import IsStr

from tests.external.storage_example import storage_example


@pytest.mark.parametrize(
    "discovery, name",
    [
        ("conftest", "custom"),
        ("nested", "custom"),
        ("package", "custom"),
        ("conftest", "Custom"),
    ],
)
def test_register_backend_and_load_snapshot(discovery, name):
    plugin = f"""\
from inline_snapshot.plugin import hookimpl
from storage_backend import FileStorage

@hookimpl
def register_storages(storage_dir):
    return {{"{name}": FileStorage(storage_dir / "{name}", "{name}")}}
"""
    files = {
        "pyproject.toml": '[tool.inline-snapshot]\nstorage-dir="snapshots"',
        f"snapshots/{name}/value.txt": "stored",
        "tests/test_something.py": f"""\
from inline_snapshot import external

def test_document():
    assert "stored" == external("{name}:value.txt")
""",
    }
    if discovery == "nested":
        files["tests/conftest.py"] = plugin
        plugin = ""
    elif discovery == "package":
        files["storage_plugin.py"] = plugin
        files["custom_storage-0.1.dist-info/METADATA"] = (
            "Metadata-Version: 2.1\nName: custom-storage\nVersion: 0.1\n"
        )
        files["custom_storage-0.1.dist-info/entry_points.txt"] = (
            "[inline_snapshot]\ncustom = storage_plugin\n"
        )
        plugin = ""
    storage_example(files, plugin=plugin, storage_dir="snapshots").run_pytest(
        outcomes={"passed": 1}, changed_files={}
    )


@pytest.mark.parametrize(
    "name, tryfirst",
    [
        ("hash", False),
        ("hash", True),
        ("uuid", False),
        ("uuid", True),
        ("custom", False),
    ],
)
def test_reject_duplicate_storage_names(name, tryfirst):
    plugin = f"""\
from inline_snapshot.plugin import hookimpl
from storage_backend import FileStorage

@hookimpl(tryfirst={tryfirst!r}, trylast={not tryfirst!r})
def register_storages(storage_dir):
    return {{"{name}": FileStorage(storage_dir / "{name}", "{name}")}}
"""
    files = {"tests/test_something.py": "def test_document(): pass\n"}
    if name == "custom":
        files["tests/conftest.py"] = plugin
    storage_example(files, plugin=plugin).run_pytest(
        returncode=3,
        outcomes={},
        stderr=IsStr(
            regex=rf"(?s).*UsageError: storage '{name}' is already registered.*"
        ),
        changed_files={},
    )


@pytest.mark.parametrize(
    "name",
    ["", "bad:name", "with space", "with-hyphen", "with_underscore", "abc1", "ä", 1],
)
def test_reject_invalid_storage_names(name):
    storage_example(
        {"tests/test_something.py": "def test_document(): pass\n"},
        plugin=f"""\
from inline_snapshot.plugin import hookimpl
from storage_backend import FileStorage

@hookimpl
def register_storages(storage_dir):
    return {{{name!r}: FileStorage(storage_dir / "documents", {name!r})}}
""",
    ).run_pytest(
        returncode=3,
        outcomes={},
        env={"PYTHONIOENCODING": "utf-8"},
        stderr=IsStr(
            regex=r"(?s).*UsageError: storage names must contain only ASCII letters.*"
        ),
        changed_files={},
    )
