from inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


def test_xdist():
    Example(
        """\
from inline_snapshot import snapshot

def test_a():
    assert 1==snapshot()
"""
    ).run_pytest(
        ["--inline-snapshot=create", "-n=auto"],
        stderr=snapshot(
            "ERROR: --inline-snapshot=create can not be combined with xdist\n"
        ),
        returncode=4,
    )


def test_xdist_disabled():
    Example(
        """\
from inline_snapshot import snapshot

def test_a():
    assert 1==snapshot(5)
"""
    ).run_pytest(
        ["-n=auto"],
        report=snapshot(
            """\
INFO: inline-snapshot was disabled because you used xdist. This means that tests
with snapshots will continue to run, but snapshot(x) will only return x and
inline-snapshot will not be able to fix snapshots or generate reports.\
"""
        ),
        returncode=snapshot(1),
        outcomes=snapshot({"failed": 1}),
    )


def test_xdist_and_disable():
    e = Example(
        """\
from inline_snapshot import snapshot

def test_a():
    assert 1==snapshot(2)
"""
    )

    e.run_pytest(
        ["-n=auto", "--inline-snapshot=disable"],
        report=snapshot(""),
        stderr=snapshot(""),
        returncode=1,
    )

    e.run_pytest(
        ["-n=auto", "--inline-snapshot=fix"],
        report=snapshot(""),
        stderr=snapshot(
            "ERROR: --inline-snapshot=fix can not be combined with xdist\n"
        ),
        returncode=4,
    )

    Example(
        {
            "pyproject.toml": """\
[tool.inline-snapshot]
default-flags = ["fix"]
""",
            "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_a():
    assert 1==snapshot(2)
""",
        }
    ).run_pytest(
        ["-n=auto"],
        report=snapshot(
            """\
INFO: inline-snapshot was disabled because you used xdist. This means that tests
with snapshots will continue to run, but snapshot(x) will only return x and
inline-snapshot will not be able to fix snapshots or generate reports.\
"""
        ),
        stderr=snapshot(""),
        returncode=1,
    )


def test_xdist_zero_processes():
    Example(
        """\
from inline_snapshot import snapshot

def test_a():
    assert 1==snapshot(2)
"""
    ).run_pytest(
        ["-n=0", "--inline-snapshot=short-report"],
        outcomes=snapshot({"failed": 1, "errors": 1}),
        report=snapshot(
            """\
Error: one snapshot has incorrect values (--inline-snapshot=fix)
You can also use --inline-snapshot=review to approve the changes interactively\
"""
        ),
        stderr=snapshot(""),
        returncode=1,
    )
