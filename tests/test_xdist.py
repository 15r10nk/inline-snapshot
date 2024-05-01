from inline_snapshot import snapshot


def test_xdist(project):

    project.setup(
        """\

def test_a():
    assert 1==snapshot()
"""
    )

    result = project.run("--inline-snapshot=create", "-n=auto")

    assert "\n".join(result.stderr.lines).strip() == snapshot(
        "ERROR: inline-snapshot can not be combined with xdist"
    )

    assert result.ret == 4


def test_xdist_disabled(project):

    project.setup(
        """\

def test_a():
    assert 1==snapshot(1)
"""
    )

    result = project.run("-n=auto")

    assert result.report == snapshot(
        "INFO: inline-snapshot was disabled because you used xdist"
    )

    assert result.ret == 0
