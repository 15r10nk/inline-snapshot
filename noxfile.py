from pathlib import Path

import nox
from nox_poetry import session

nox.options.sessions = ["test", "coverage", "mypy"]  # "docs"]

python_versions = ["3.7", "3.8", "3.9", "3.10", "3.11", "3.12"]


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
    session.install("mypy", "pytest", "hypothesis", ".")
    session.run("mypy", "inline_snapshot", "tests")


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
    )
    session.env["COVERAGE_PROCESS_START"] = str(
        Path(__file__).parent / "pyproject.toml"
    )
    args = [] if session.posargs else ["-n", "auto", "-v"]

    session.env["TOP"] = str(Path(__file__).parent)
    session.run(
        "coverage",
        "run",
        "-m",
        "pytest",
        "--doctest-modules",
        *args,
        "tests",
        "inline_snapshot",
        *session.posargs
    )


@session(python="python3.10")
def docs(session):
    session.install("mkdocs", "mkdocs-material[imaging]", "mkdocstrings[python]")
    session.run("mkdocs", "build", *session.posargs)


@session(python="python3.10")
def docs_serve(session):
    session.install("mkdocs", "mkdocs-material[imaging]", "mkdocstrings[python]")
    session.run("mkdocs", "serve", *session.posargs)
