from inline_snapshot import snapshot
from inline_snapshot.testing import Example


def test_example():

    e = Example(
        {
            "test_a.py": """
from inline_snapshot import snapshot

def test_a():
    assert 1==snapshot(2)
    """,
            "test_b.py": "1+1",
        },
    )

    e.run_pytest(
        ["--inline-snapshot=create,fix"],
    )

    e.run_inline(
        ["--inline-snapshot=fix"],
        reported_categories=snapshot(["fix"]),
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot({}),
    )
