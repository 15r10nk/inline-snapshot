from inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


def test_ci_run():
    e = Example(
        """
from inline_snapshot import snapshot
def test_something():
    assert type(snapshot(5)) is int

    """
    )

    e.run_pytest(
        env={"CI": "true"},
        report=snapshot(
            """\
INFO: CI run was detected because environment variable "CI" was defined.
inline-snapshot runs with --inline-snapshot=disable by default in CI. This means
that tests with snapshots will continue to run, but snapshot(x) will only return
x and inline-snapshot will not be able to fix snapshots or generate reports. You
can change this by using --inline-snapshot=report for example.\
"""
        ),
    )


def test_ci_and_fix():
    Example(
        """
from inline_snapshot import snapshot
def test_something():
    assert 5==snapshot(2)

    """
    ).run_pytest(
        ["--inline-snapshot=fix"],
        env={"CI": "true"},
        report=snapshot(
            """\
-------------------------------- Fix snapshots ---------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -1,6 +1,6 @@                                                              |
|                                                                              |
|                                                                              |
|  from inline_snapshot import snapshot                                        |
|  def test_something():                                                       |
| -    assert 5==snapshot(2)                                                   |
| +    assert 5==snapshot(5)                                                   |
+------------------------------------------------------------------------------+
These changes will be applied, because you used fix\
"""
        ),
        returncode=1,
    )


def test_no_ci_run():
    Example(
        """
from inline_snapshot import snapshot
def test_something():
    assert not isinstance(snapshot(5),int)

    """
    ).run_pytest(
        env={"TEAMCITY_VERSION": "true", "PYCHARM_HOSTED": "true"},
    )
