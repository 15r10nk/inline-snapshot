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
INFO: inline-snapshot runs with --inline-snapshot=disabled by default in CI.\
"""
        ),
    )

    e.run_pytest(
        ["--inline-snapshot=disable"],
        env={"CI": "true"},
        report=snapshot(""),
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
