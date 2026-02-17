from inline_snapshot import snapshot
from inline_snapshot.testing import Example


def test_datetime_with_timezone():
    Example(
        {
            "test_something.py": """\
from datetime import datetime, timezone
from inline_snapshot import snapshot


def test_datetime():
    dt = datetime(2026, 2, 16, 5, 0, tzinfo=timezone.utc)
    assert dt == snapshot()
""",
        }
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from datetime import datetime, timezone
from inline_snapshot import snapshot


def test_datetime():
    dt = datetime(2026, 2, 16, 5, 0, tzinfo=timezone.utc)
    assert dt == snapshot(datetime(2026, 2, 16, hour=5, tzinfo=timezone.utc))
"""
            }
        ),
    ).run_inline()


def test_time_with_timezone():
    Example(
        {
            "test_something.py": """\
from datetime import time, timezone
from inline_snapshot import snapshot


def test_time():
    t = time(12, 30, tzinfo=timezone.utc)
    assert t == snapshot()
""",
        }
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from datetime import time, timezone
from inline_snapshot import snapshot


def test_time():
    t = time(12, 30, tzinfo=timezone.utc)
    assert t == snapshot(time(hour=12, minute=30, tzinfo=timezone.utc))
"""
            }
        ),
    ).run_inline()


def test_custom_timezone_with_offset_only():
    Example(
        {
            "test_something.py": """\
from datetime import datetime, timedelta, timezone
from inline_snapshot import snapshot


def test_custom_tz():
    tz = timezone(timedelta(hours=5))
    dt = datetime(2026, 2, 16, 5, 0, tzinfo=tz)
    assert dt == snapshot()
""",
        }
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from datetime import datetime, timedelta, timezone
from inline_snapshot import snapshot


def test_custom_tz():
    tz = timezone(timedelta(hours=5))
    dt = datetime(2026, 2, 16, 5, 0, tzinfo=tz)
    assert dt == snapshot(
        datetime(
            2026, 2, 16, hour=5, tzinfo=timezone(timedelta(seconds=18000), "UTC+05:00")
        )
    )
"""
            }
        ),
    ).run_inline()


def test_custom_timezone_with_name():
    Example(
        {
            "test_something.py": """\
from datetime import datetime, timedelta, timezone
from inline_snapshot import snapshot


def test_custom_tz_named():
    tz = timezone(timedelta(hours=-5), "EST")
    dt = datetime(2026, 2, 16, 5, 0, tzinfo=tz)
    assert dt == snapshot()
""",
        }
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from datetime import datetime, timedelta, timezone
from inline_snapshot import snapshot


def test_custom_tz_named():
    tz = timezone(timedelta(hours=-5), "EST")
    dt = datetime(2026, 2, 16, 5, 0, tzinfo=tz)
    assert dt == snapshot(
        datetime(
            2026,
            2,
            16,
            hour=5,
            tzinfo=timezone(timedelta(days=-1, seconds=68400), "EST"),
        )
    )
"""
            }
        ),
    ).run_inline()
