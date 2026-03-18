import pytest

from inline_snapshot import snapshot
from inline_snapshot.testing import Example


def _format_call(args, kwargs):
    """Format a Call constructor with args and kwargs"""
    args_str = ", ".join(str(a) for a in args)
    kwargs_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    parts = [p for p in [args_str, kwargs_str] if p]
    return f"Call({', '.join(parts)})"


@pytest.mark.parametrize("actual_args", [(), (1,), (1, 0), (1, 0, 2), (5,)])
@pytest.mark.parametrize(
    "actual_kwargs", [{}, {"kw1": 2}, {"kw1": 2, "kw2": 3}, {"x": 1}]
)
@pytest.mark.parametrize("snap_args", [(), (0,), (0, 1), (1, 2, 3), (5,)])
@pytest.mark.parametrize(
    "snap_kwargs", [{}, {"kw2": 5}, {"kw1": 5}, {"kw1": 2, "kw2": 3}, {"x": 1}]
)
def test_call_fix(actual_args, actual_kwargs, snap_args, snap_kwargs):
    """Test that fix flag properly updates mismatched Call snapshots"""

    actual_call = _format_call(actual_args, actual_kwargs)
    snap_call = _format_call(snap_args, snap_kwargs)

    # Skip cases where actual and snapshot are the same
    if actual_call == snap_call:
        pytest.skip("No mismatch to fix")

    Example(
        {
            "call_type.py": """\
class Call:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __eq__(self, other):
        if not isinstance(other, Call):
            return NotImplemented
        return self.args == other.args and self.kwargs == other.kwargs
""",
            "conftest.py": """\
from inline_snapshot.plugin import customize
from call_type import Call

@customize
def call_handler(value, builder):
    if isinstance(value, Call):
        return builder.create_call(
            Call,
            list(value.args),
            dict(value.kwargs),
        )
""",
            "test_call.py": f"""\
from inline_snapshot import snapshot
from call_type import Call

def test_thing():
    assert {actual_call} == snapshot({snap_call}), "not equal"
""",
        }
    ).run_inline(
        ["--inline-snapshot=fix"],
    ).run_inline()


def test_call_map_exception():
    """Test that CustomCall._map raises TypeError with proper message when call fails"""
    Example(
        {
            "bad_call_type.py": """\
class BadCall:
    def __init__(self, *args):
        self.args = args
        assert args, "args required"

    def __eq__(self, other):
        if not isinstance(other, BadCall):
            return NotImplemented
        return True
""",
            "conftest.py": """\
from inline_snapshot.plugin import customize
from bad_call_type import BadCall

@customize
def call_handler(value, builder):
    if isinstance(value, BadCall):
        return builder.create_call(
            BadCall,
            [],
        )
""",
            "test_call.py": """\
from inline_snapshot import snapshot
from bad_call_type import BadCall

def test_thing():
    assert BadCall(1) == snapshot(BadCall(4))
""",
        }
    ).run_inline(
        ["--inline-snapshot=fix"],
        raises=snapshot("TypeError: cannot call CustomCode('BadCall')()"),
    )
