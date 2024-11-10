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
        "ERROR: --inline-snapshot=create can not be combined with xdist"
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


def test_xdist_and_disable(project):

    project.setup(
        """\

def test_a():
    assert 1==snapshot(2)
"""
    )

    def filter_error_lines(result):
        lines = result.stderr.lines
        return [
            line
            for line in lines
            if line
            not in (
                'No entry for terminal type "unknown";',
                "using dumb terminal settings.",
            )
        ]

    result = project.run("-n=auto", "--inline-snapshot=disable")

    assert result.report == snapshot("")

    assert filter_error_lines(result) == snapshot([])

    assert result.ret == 1

    result = project.run("-n=auto", "--inline-snapshot=fix")

    assert result.report == snapshot("")

    assert filter_error_lines(result) == snapshot(
        ["ERROR: --inline-snapshot=fix can not be combined with xdist", ""]
    )

    assert result.ret == 4

    project.pyproject(
        """\
[tool.inline-snapshot]
default-flags = ["fix"]
"""
    )

    result = project.run("-n=auto")

    assert result.report == snapshot(
        "INFO: inline-snapshot was disabled because you used xdist"
    )

    assert filter_error_lines(result) == snapshot([])

    assert result.ret == 0
