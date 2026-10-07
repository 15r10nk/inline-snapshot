import json
import subprocess
import sys
from pathlib import Path


def test_survey_snapshot_imports(tmp_path):
    repo = tmp_path / "example"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "test_examples.py").write_text(
        "from inline_snapshot import snapshot as expected\n"
        "import inline_snapshot as inline\n"
        "from ._inline_snapshot import snapshot\n"
        "assert {} == expected({'key': [1, 2]})\n"
        "assert 1 == inline.snapshot(obj=1)\n"
        "assert 'text' == snapshot('text')\n"
        "assert 1 == unrelated.snapshot(1)\n"
        "text = 'snapshot(123)'\n",
        encoding="utf-8",
    )
    (repo / "unrelated.py").write_text(
        "def snapshot(value): return value\nsnapshot(1)\n", encoding="utf-8"
    )
    (repo / "broken.py").write_text("this is not valid Python!", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Benchmark test",
            "-c",
            "user.email=benchmark@example.invalid",
            "-c",
            f"core.hooksPath={tmp_path / 'empty-hooks'}",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    # Untracked files must not affect the corpus.
    (repo / "untracked.py").write_text(
        "from inline_snapshot import snapshot\nsnapshot(999)\n", encoding="utf-8"
    )
    script = Path(__file__).resolve().parents[1] / "scripts" / "survey_snapshots.py"
    result = subprocess.run(
        [sys.executable, str(script), str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)["repositories"]["example"]
    assert data["calls"] == 3
    assert data["files"] == 1
    assert data["shapes"] == {"Dict": 1, "int": 1, "str": 1}
    assert data["comparisons"] == {"Eq": 3}
    assert data["tracked_changes"] is False
    assert data["largest"][0]["line"] == 4
    assert [entry["file"] for entry in data["skipped_files"]] == ["broken.py"]
