from inline_snapshot.testing import Example


def test_fstring_139():
    Example(
        """
from inline_snapshot import snapshot
snapshot(f'')

def test_a():
    return None
    """
    ).run_pytest(returncode=0)
