from .example import Example
from inline_snapshot import snapshot


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
        "--inline-snapshot=create,fix",
    )

    e.run_inline(
        "fix",
        reported_flags=snapshot(["fix"]),
    ).run_inline(
        "fix",
        changed_files=snapshot({}),
    )
