from inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


def test_use_snapshot_updates():

    expected_report = snapshot("")

    Example(
        {
            "pyproject.toml": f"""\
[tool.inline-snapshot]
""",
            "tests/test_a.py": """\
from inline_snapshot import snapshot

def test_a():
    assert 5 == snapshot(2+3)
""",
        }
    ).run_pytest(
        ["--inline-snapshot=review"], changed_files=snapshot({}), report=expected_report
    ).run_pytest(
        ["--inline-snapshot=report"], changed_files=snapshot({}), report=expected_report
    ).run_pytest(
        ["--inline-snapshot=update"],
        changed_files=snapshot(
            {
                "tests/test_a.py": """\
from inline_snapshot import snapshot

def test_a():
    assert 5 == snapshot(5)
"""
            }
        ),
        report=snapshot(
            """\
------------------------------- Update snapshots -------------------------------
+------------------------------ tests/test_a.py -------------------------------+
| @@ -1,4 +1,4 @@                                                              |
|                                                                              |
|  from inline_snapshot import snapshot                                        |
|                                                                              |
|  def test_a():                                                               |
| -    assert 5 == snapshot(2+3)                                               |
| +    assert 5 == snapshot(5)                                                 |
+------------------------------------------------------------------------------+
These changes will be applied, because you used update\
"""
        ),
    )
