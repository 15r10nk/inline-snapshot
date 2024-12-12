import warnings

from inline_snapshot import snapshot
from inline_snapshot.extra import warns


def test_warns():

    def warning():
        warnings.warn_explicit(
            message="bad things happen",
            category=SyntaxWarning,
            filename="file.py",
            lineno=5,
        )

    with warns(
        snapshot([("file.py", 5, "SyntaxWarning: bad things happen")]),
        include_line=True,
        include_file=True,
    ):
        warning()

    with warns(
        snapshot([("file.py", "SyntaxWarning: bad things happen")]),
        include_file=True,
    ):
        warning()

    with warns(
        snapshot(["SyntaxWarning: bad things happen"]),
    ):
        warning()
