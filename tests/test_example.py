from .example import Example


def test_diff_multiple_files():

    Example(
        """
from inline_snapshot import snapshot

def test_a():
    assert 1==snapshot(2)
    """,
    ).run_pytest(
        "--inline-snapshot=create,fix",
    )
