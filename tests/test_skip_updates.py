import pytest

from inline_snapshot import Is
from inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


@pytest.mark.parametrize("values", [(1, 2), (2, 1)])
def test_skip_updates_preserves_comparison_consistency(values):
    code = f"""\
from inline_snapshot import snapshot

def test_a():
    for x in {values!r}:
        assert x == snapshot(1)
"""
    Example(
        {
            "pyproject.toml": """\
[tool.inline-snapshot]
show-updates=false
""",
            "tests/test_a.py": code,
        }
    ).run_inline(
        ["--inline-snapshot=fix"],
        raises="AssertionError",
        reported_categories=Is({"fix"} if values[0] == 2 else set()),
        changed_files=Is(
            {"tests/test_a.py": code.replace("snapshot(1)", "snapshot(2)")}
            if values[0] == 2
            else {}
        ),
    )


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
        changed_files=snapshot({"tests/test_a.py": """\
from inline_snapshot import snapshot

def test_a():
    assert 5 == snapshot(5)
"""}),
        report=snapshot("""\
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
"""),
    )
