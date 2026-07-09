from inline_snapshot import snapshot
from inline_snapshot._config import Config
from inline_snapshot._config import read_config
from inline_snapshot._exceptions import UsageError
from inline_snapshot.testing import Example

file_to_trim = {
    "test_a.py": """\
from inline_snapshot import snapshot

def test_a():
    assert 1 <= snapshot(5)
    assert 1 == snapshot(2)
""",
}

trimmed_files = snapshot({"test_a.py": """\
from inline_snapshot import snapshot

def test_a():
    assert 1 <= snapshot(1)
    assert 1 == snapshot(2)
"""})


def test_config_pyproject():

    Example(
        {
            **file_to_trim,
            "pyproject.toml": """
[tool.inline-snapshot]
default-flags = ["trim"]
            """,
        }
    ).run_pytest(
        changed_files=trimmed_files,
        returncode=snapshot(1),
        error="""\
>       assert 1 == snapshot(2)
E       assert 1 == 2
E        +  where 2 = snapshot(2)
""",
        outcomes={"failed": 1, "errors": 1},
    )


def test_config_env():
    e = Example(file_to_trim)

    e.run_pytest(
        env={"INLINE_SNAPSHOT_DEFAULT_FLAGS": "trim"},
        changed_files=trimmed_files,
        returncode=snapshot(1),
        error="""\
>       assert 1 == snapshot(2)
E       assert 1 == 2
E        +  where 2 = snapshot(2)
""",
        outcomes={"failed": 1, "errors": 1},
    )

    e.run_pytest(
        stdin=b"\n",
        env={"INLINE_SNAPSHOT_DEFAULT_FLAGS": "trim"},
        changed_files=trimmed_files,
        returncode=snapshot(1),
        error="""\
>       assert 1 == snapshot(2)
E       assert 1 == 2
E        +  where 2 = snapshot(2)
""",
        outcomes={"failed": 1, "errors": 1},
    )


def test_shortcuts():

    Example(
        {
            **file_to_trim,
            "pyproject.toml": """
[tool.inline-snapshot.shortcuts]
strim=["trim"]
            """,
        }
    ).run_pytest(
        ["--strim"],
        changed_files=trimmed_files,
        returncode=snapshot(1),
        error="""\
>       assert 1 == snapshot(2)
E       assert 1 == 2
E        +  where 2 = snapshot(2)
""",
        outcomes={"failed": 1, "errors": 1},
    )


def test_default_shortcuts():

    Example(
        {
            **file_to_trim,
            "pyproject.toml": """
            """,
        }
    ).run_pytest(
        ["--fix"],
        changed_files=snapshot({"test_a.py": """\
from inline_snapshot import snapshot

def test_a():
    assert 1 <= snapshot(5)
    assert 1 == snapshot(1)
"""}),
        returncode=1,
        outcomes={"passed": 1, "errors": 1},
    )


def test_incorrect_storage():
    Example({"pyproject.toml": """
[tool.inline-snapshot]
default-storage="incorrect"
    """}).run_pytest(
        stderr=snapshot(
            'ERROR: default-storage has to be uuid or hash but is "incorrect"\n'
        ),
        returncode=snapshot(4),
        outcomes={},
    )


def test_test_dir_config(tmp_path):
    (tmp_path / "tests_a").mkdir()
    (tmp_path / "tests_b").mkdir()
    pyproject = tmp_path / "pyproject.toml"

    pyproject.write_text(
        """\
[tool.inline-snapshot]
test-dir = "tests_a"
""",
        encoding="utf-8",
    )

    assert read_config(pyproject, Config()).test_directories == [tmp_path / "tests_a"]

    pyproject.write_text(
        """\
[tool.inline-snapshot]
test-dir = ["tests_a", "tests_b"]
""",
        encoding="utf-8",
    )

    assert read_config(pyproject, Config()).test_directories == [
        tmp_path / "tests_a",
        tmp_path / "tests_b",
    ]


def test_incorrect_test_dir(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """\
[tool.inline-snapshot]
test-dir = 1
""",
        encoding="utf-8",
    )

    try:
        read_config(pyproject, Config())
    except UsageError as e:
        assert str(e) == snapshot(
            "test-dir has to be a directory or list of directories"
        )
    else:
        assert False
