import pytest

from inline_snapshot._rewrite_code import ChangeRecorder
from inline_snapshot._rewrite_code import SourcePosition
from inline_snapshot._rewrite_code import SourceRange
from inline_snapshot._rewrite_code import end_of
from inline_snapshot._rewrite_code import range_of
from inline_snapshot._rewrite_code import start_of


def test_range():
    a = SourcePosition(1, 2)
    b = SourcePosition(2, 5)
    assert a < b
    r = SourceRange(a, b)
    assert start_of(r) == a
    assert end_of(r) == b

    assert range_of(r) == r

    with pytest.raises(ValueError):
        SourceRange(b, a)


def test_rewrite(tmp_path):
    file = tmp_path / "file.txt"
    file.write_text(
        """
12345
12345
12345
""",
        "utf-8",
    )

    recorder = ChangeRecorder()
    s = recorder.new_change()

    s.replace(((2, 2), (2, 3)), "a", filename=file)
    s.delete(((3, 2), (3, 3)), filename=file)
    s.insert((4, 2), "c", filename=file)

    assert recorder.num_fixes() == 1
    recorder.fix_all()

    assert (
        file.read_text("utf-8")
        == """
12a45
1245
12c345
"""
    )
