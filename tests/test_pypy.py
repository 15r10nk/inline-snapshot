import sys

import pytest

from inline_snapshot import snapshot
from inline_snapshot.testing import Example


@pytest.mark.no_rewriting
def test_pypy():

    no_cpython = sys.implementation.name != "cpython"

    report = (
        snapshot(
            """\
INFO: inline-snapshot was disabled because pypy is not supported. This means
that tests with snapshots will continue to run, but snapshot(x) will only return
x and inline-snapshot will not be able to fix snapshots or generate reports.\
"""
        )
        if sys.implementation.name == "pypy"
        else snapshot(
            """\
-------------------------------- Fix snapshots ---------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -1,6 +1,6 @@                                                              |
|                                                                              |
|  from inline_snapshot import snapshot                                        |
|                                                                              |
|  def test_example():                                                         |
| -    assert 1+1==snapshot(3)                                                 |
| +    assert 1+1==snapshot(2)                                                 |
+------------------------------------------------------------------------------+
These changes will be applied, because you used fix\
"""
        )
    )

    Example(
        """\
from inline_snapshot import snapshot

def test_example():
    assert 1+1==snapshot(3)

    """
    ).run_pytest(["--inline-snapshot=fix"], report=report, returncode=1).run_pytest(
        ["--inline-snapshot=disable"], report="", returncode=1 if no_cpython else 0
    )
