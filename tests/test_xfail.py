from inline_snapshot import snapshot
from inline_snapshot.testing import Example


def test_xfail_without_condition():

    Example(
        """\
import pytest

@pytest.mark.xfail
def test_a():
    assert 1==snapshot(5)
"""
    ).run_pytest(
        ["--inline-snapshot=fix"],
        report=snapshot(""),
        returncode=snapshot(0),
        stderr=snapshot(""),
        changed_files=snapshot({}),
    )


def test_xfail_True():
    Example(
        """\
import pytest
from inline_snapshot import snapshot

@pytest.mark.xfail(True,reason="...")
def test_a():
    assert 1==snapshot(5)
"""
    ).run_pytest(
        ["--inline-snapshot=fix"],
        report=snapshot(""),
        returncode=snapshot(0),
        stderr=snapshot(""),
        changed_files=snapshot({}),
    )


def test_xfail_False():
    Example(
        """\
import pytest
from inline_snapshot import snapshot

@pytest.mark.xfail(False,reason="...")
def test_a():
    assert 1==snapshot(5)
"""
    ).run_pytest(
        ["--inline-snapshot=fix"],
        report=snapshot(
            """\
-------------------------------- Fix snapshots ---------------------------------
+----------------------------- test_something.py ------------------------------+
| @@ -3,4 +3,4 @@                                                              |
|                                                                              |
|                                                                              |
|  @pytest.mark.xfail(False,reason="...")                                      |
|  def test_a():                                                               |
| -    assert 1==snapshot(5)                                                   |
| +    assert 1==snapshot(1)                                                   |
+------------------------------------------------------------------------------+
These changes will be applied, because you used fix\
"""
        ),
        returncode=snapshot(1),
        stderr=snapshot(""),
        changed_files=snapshot(
            {
                "test_something.py": """\
import pytest
from inline_snapshot import snapshot

@pytest.mark.xfail(False,reason="...")
def test_a():
    assert 1==snapshot(1)
"""
            }
        ),
    )
