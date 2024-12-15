from inline_snapshot import snapshot
from inline_snapshot.extra import raises
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
        returncode=1,
    )

    e.run_inline(
        ["--inline-snapshot=fix"],
        reported_categories=snapshot(["fix"]),
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot({}),
    )


def test_no_tests():

    with raises(snapshot("UsageError: no test_*() functions in the example")):
        Example("").run_inline()


def test_throws_exception():

    with raises(snapshot("Exception: test")):
        Example(
            """\
def test_a():
    raise Exception("test")

        """
        ).run_inline()
