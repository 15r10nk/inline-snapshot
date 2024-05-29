import os
from pathlib import Path

import nox
from nox_poetry import session

nox.options.sessions = ["test", "coverage", "mypy"]  # "docs"]

python_versions = ["3.8", "3.9", "3.10", "3.11", "3.12"]


@session(python="python3.10")
def coverage(session):
    session.install("coverage[toml]")
    session.env["TOP"] = str(Path(__file__).parent)
    try:
        session.run("coverage", "combine")
    except:
        pass
    session.run("coverage", "html")
    session.run("coverage", "report", "--fail-under", "100")
    session.run("coverage", "erase")


@session(python=python_versions)
def mypy(session):
    session.install("mypy", "pytest", "hypothesis", "dirty-equals", "pydantic", ".")
    args = ["inline_snapshot", "tests"]
    if session.posargs:
        args = session.posargs
    session.run("mypy", *args)


@session(python=python_versions)
def test(session):
    session.install(
        ".",
        "pytest",
        "hypothesis",
        "pytest-subtests",
        "pytest",
        "coverage",
        "pytest-xdist",
        "coverage-enable-subprocess",
        "dirty-equals",
        "time-machine",
        "mypy",
        "pyright",
        "pydantic",
    )

    cmd = []
    if (
        session.python in (python_versions[0], python_versions[-1])
        or "CI" in os.environ
    ):
        cmd += ["coverage", "run", "-m"]
        session.env["COVERAGE_PROCESS_START"] = str(
            Path(__file__).parent / "pyproject.toml"
        )
        session.env["TOP"] = str(Path(__file__).parent)
    else:
        cmd = ["python", "-m"]

    args = [] if session.posargs else ["-n", "auto", "-v"]

    session.run(
        *cmd,
        "pytest",
        "--doctest-modules",
        *args,
        "tests",
        "inline_snapshot",
        *session.posargs
    )


@session(python="python3.10")
def mkdocs(session):
    session.install(
        "mkdocs",
        "mkdocs-material[imaging]",
        "mkdocstrings[python]",
        "markdown-exec[ansi]",
        "docs/plugins",
        "pytest",
        ".",
    )
    session.run("mkdocs", *session.posargs)


@session(python="python3.10")
def docs_serve(session):
    session.install(
        "mkdocs",
        "mkdocs-material[imaging]",
        "mkdocstrings[python]",
        "markdown-exec[ansi]",
        "docs/plugins",
        "pytest",
        ".",
    )
    session.run("mkdocs", "serve", *session.posargs)
