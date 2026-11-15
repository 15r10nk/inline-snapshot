import pytest


@pytest.mark.parametrize("flags", ["report", "fix"])
def test_normal_run_does_not_need_snapshot_catalog(storage_example, flags):
    storage_example(
        {
            ".inline-snapshot/custom/value.txt": "stored",
            "tests/test_something.py": """\
from inline_snapshot import external

def test_document():
    assert "stored" == external("custom:value.txt")
""",
        },
        backend="OfflineCatalogStorage",
    ).run_pytest(
        [f"--inline-snapshot={flags}"], outcomes={"passed": 1}, changed_files={}
    )


def test_trim_deletes_only_unreferenced_snapshots(storage_example):
    storage_example(
        {
            ".inline-snapshot/custom/value.txt": "stored",
            ".inline-snapshot/custom/unused.txt": "unused",
            "tests/test_something.py": """\
from inline_snapshot import external

def test_document():
    assert "stored" == external("custom:value.txt")
""",
        },
    ).run_pytest(
        ["--inline-snapshot=trim"],
        outcomes={"passed": 1},
        changed_files={".inline-snapshot/custom/unused.txt": None},
    )


def test_selected_tests_do_not_need_snapshot_catalog(storage_example):
    storage_example(
        {
            ".inline-snapshot/custom/value.txt": "stored",
            "tests/test_something.py": """\
from inline_snapshot import external

def test_selected():
    assert "stored" == external("custom:value.txt")

def test_other():
    assert "stored" == external("custom:value.txt")
""",
        },
        backend="OfflineCatalogStorage",
    ).run_pytest(
        ["-k", "test_selected"],
        env={"INLINE_SNAPSHOT_DEFAULT_FLAGS": "trim"},
        outcomes={"passed": 1, "deselected": 1},
        changed_files={},
    )
