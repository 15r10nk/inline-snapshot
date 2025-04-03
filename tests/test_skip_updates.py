from inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


def test_skip_snapshot_updates():

    expected_report = snapshot(
        """\
1 updates are hidden. Please report why you do not want these updates so that
inline-snapshot can create better snapshots in the future.
You can find more information about updates here:
https://15r10nk.github.io/inline-snapshot/latest/categories/#update\
"""
    )

    Example(
        {
            "pyproject.toml": f"""\
[tool.inline-snapshot]
skip-snapshot-updates-for-now=true
""",
            "test_a.py": """\
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
                "test_a.py": """\
from inline_snapshot import snapshot

def test_a():
    assert 5 == snapshot(5)
"""
            }
        ),
        report=snapshot(
            """\
------------------------------- Update snapshots -------------------------------
+--------------------------------- test_a.py ----------------------------------+
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
