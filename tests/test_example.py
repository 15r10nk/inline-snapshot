from executing import Source

from .example import Example
from inline_snapshot import HasRepr
from inline_snapshot import snapshot
from inline_snapshot._change import Replace


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
        changes=snapshot(
            [
                Replace(
                    flag="fix",
                    source=HasRepr(Source, "<source test_a.py>"),
                    node="Constant(value=2)",
                    new_code="1",
                    old_value=2,
                    new_value=1,
                )
            ]
        ),
    ).run_inline(
        "fix",
        changed_files=snapshot({}),
    )
