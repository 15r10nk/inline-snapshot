import shutil
import sys

from inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


def test_run_pytester():
    Example(
        {
            "conftest.py": """\
pytest_plugins = ["pytester"]
""",
            "test_things.py": """\
from inline_snapshot import snapshot

def test_not_pytester():
    assert "hey" == snapshot()

def test_pytester(pytester):
    pytester.runpytest()
""",
        }
    ).run_pytest(
        ["--inline-snapshot=create"],
        changed_files=snapshot({"test_things.py": """\
from inline_snapshot import snapshot

def test_not_pytester():
    assert "hey" == snapshot("hey")

def test_pytester(pytester):
    pytester.runpytest()
"""}),
        returncode=1,
        outcomes={"passed": 2, "errors": 1},
    ).run_pytest(
        ["--inline-snapshot=disable"], outcomes={"passed": 2}
    )


def test_pytester_moved_folder_with_stale_pyc(pytester, monkeypatch):
    monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)

    original = pytester.path / "original"
    moved = pytester.path / "moved"
    original.mkdir()

    (original / "test_snapshot.py").write_text(
        """\
from inline_snapshot import snapshot


def test_snapshot():
    assert "value" == snapshot()
""",
        encoding="utf-8",
    )

    result = pytester.run(
        sys.executable,
        "-m",
        "pytest",
        "--inline-snapshot=disable",
        "-q",
        str(original),
    )

    assert result.ret == 1

    shutil.move(original, moved)

    result = pytester.run(
        sys.executable,
        "-m",
        "pytest",
        "--inline-snapshot=create",
        "-q",
        str(moved),
    )

    assert result.ret == 1
    result.stdout.fnmatch_lines(["*1 passed*"])
    result.stderr.no_fnmatch_line("*AssertionError:*")

    result = pytester.run(
        sys.executable,
        "-m",
        "pytest",
        "--inline-snapshot=disable",
        "-q",
        str(moved),
    )
    assert result.ret == 0
