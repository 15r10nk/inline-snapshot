from inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


def test_default_arg():

    e = Example(
        {
            "conftest.py": """\
from inline_snapshot.plugin import customize

class InlineSnapshotPlugin:
    @customize
    def handler(self,value,builder):
        if value==5:
            return builder.with_default(5,builder.create_code("8"))
""",
            "test_a.py": """\
from inline_snapshot import snapshot
def test_a():
    assert 5==snapshot()
""",
        }
    )

    e.run_inline(
        ["--inline-snapshot=create"],
        raises=snapshot(
            """\
UsageError:
default value can not be an Custom value\
"""
        ),
    )
