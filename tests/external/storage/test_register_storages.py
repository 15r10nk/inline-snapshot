import pytest
from dirty_equals import IsStr

from inline_snapshot import Is


@pytest.mark.parametrize("discovery", ["conftest", "nested", "package"])
@pytest.mark.parametrize("name", ["custom", "Custom"])
def test_register_backend_and_load_snapshot(storage_example, discovery, name):
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


def test_create_and_update_snapshot(storage_example):
    source = """\
from inline_snapshot import external

def test_document():
    assert "draft" == external("custom:.txt")
"""
    created_source = source.replace("custom:.txt", "custom:value.txt")
    storage_example({"tests/test_something.py": source}).run_inline(
        ["--inline-snapshot=create"],
        changed_files={
            ".inline-snapshot/custom/value.txt": "draft",
            "tests/test_something.py": created_source,
        },
    ).replace('"draft"', '"final"').run_inline(
        ["--inline-snapshot=fix"],
        changed_files={".inline-snapshot/custom/value.txt": "final"},
    ).run_pytest(
        ["--inline-snapshot=disable"], outcomes={"passed": 1}, changed_files={}
    )


@pytest.mark.parametrize("name", ["hash", "uuid", "custom"])
@pytest.mark.parametrize("tryfirst", [False, True])
def test_reject_duplicate_storage_names(storage_example, name, tryfirst):
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
def test_reject_invalid_storage_names(storage_example, name):
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


@pytest.mark.parametrize(
    "reference, restored_file",
    [
        ("custom:value.txt", ".inline-snapshot/custom/value.txt"),
        (
            "uuid:00000000-0000-4000-8000-000000000000.txt",
            "tests/__inline_snapshot__/test_something/test_document/00000000-0000-4000-8000-000000000000.txt",
        ),
    ],
)
def test_recreate_deleted_snapshot(storage_example, reference, restored_file):
    storage_example(
        {
            "tests/test_something.py": f"""\
from inline_snapshot import external

def test_document():
    assert "stored" == external("{reference}")
""",
        }
    ).run_inline(
        ["--inline-snapshot=create,fix"],
        reported_categories={"create"},
        changed_files=Is({restored_file: "stored"}),
    ).run_pytest(
        ["--inline-snapshot=disable"], outcomes={"passed": 1}, changed_files={}
    )
