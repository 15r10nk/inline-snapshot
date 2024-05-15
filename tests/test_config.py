from .example import Example
from inline_snapshot import snapshot

trimmed_report = snapshot(
    """\
-------------------------------- Fix snapshots ---------------------------------
+--------------------------------- test_a.py ----------------------------------+
| @@ -3,5 +3,5 @@                                                              |
|                                                                              |
|                                                                              |
|  def test_a():                                                               |
|      assert 1 <= snapshot(5)                                                 |
| -    assert 1 == snapshot(2)                                                 |
| +    assert 1 == snapshot(1)                                                 |
+------------------------------------------------------------------------------+
These changes are not applied.
Use --inline-snapshot=fix to apply theme, or use the interactive mode with
--inline-snapshot=review
-------------------------------- Trim snapshots --------------------------------
+--------------------------------- test_a.py ----------------------------------+
| @@ -2,6 +2,6 @@                                                              |
|                                                                              |
|  from inline_snapshot import snapshot                                        |
|                                                                              |
|  def test_a():                                                               |
| -    assert 1 <= snapshot(5)                                                 |
| +    assert 1 <= snapshot(1)                                                 |
|      assert 1 == snapshot(2)                                                 |
+------------------------------------------------------------------------------+
These changes will be applied, because you used --inline-snapshot=trim\
"""
)


def test_config_pyproject():

    Example(
        {
            "test_a.py": """
from inline_snapshot import snapshot

def test_a():
    assert 1 <= snapshot(5)
    assert 1 == snapshot(2)
    """,
            "pyproject.toml": """
[tool.inline-snapshot]
default-flags = ["trim"]
            """,
        }
    ).run_pytest(report=trimmed_report)


def test_config_env():
    Example(
        {
            "test_a.py": """
from inline_snapshot import snapshot

def test_a():
    assert 1 <= snapshot(5)
    assert 1 == snapshot(2)
    """,
        }
    ).run_pytest(env={"INLINE_SNAPSHOT_DEFAULT_FLAGS": "trim"}, report=trimmed_report)
