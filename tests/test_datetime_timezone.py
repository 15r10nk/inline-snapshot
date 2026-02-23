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


def test_pandas_timestamp():
    Example(
        {
            "test_something.py": """\
from pandas import Timestamp
from inline_snapshot import snapshot


def test_pandas_timestamp():
    dt = Timestamp("2024-01-31 13:00:00+0000", tz="UTC")
    assert dt == snapshot()

    dt2 = Timestamp("2024-01-31 13:00:00")
    assert dt2 == snapshot()

    dt3 = Timestamp("2023-10-29 18:21:52.888000+0000", tz="UTC")
    assert dt3 == snapshot()

    dt4 = Timestamp("2024-01-31 13:00:00")
    assert dt4 == snapshot(Timestamp("2024-01-31 13:00:00"))
""",
        }
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from pandas import Timestamp
from inline_snapshot import snapshot

from datetime import datetime
from datetime import timezone


def test_pandas_timestamp():
    dt = Timestamp("2024-01-31 13:00:00+0000", tz="UTC")
    assert dt == snapshot(datetime(2024, 1, 31, hour=13, tzinfo=timezone.utc))

    dt2 = Timestamp("2024-01-31 13:00:00")
    assert dt2 == snapshot(datetime(2024, 1, 31, hour=13))

    dt3 = Timestamp("2023-10-29 18:21:52.888000+0000", tz="UTC")
    assert dt3 == snapshot(
        datetime(
            2023,
            10,
            29,
            hour=18,
            minute=21,
            second=52,
            microsecond=888000,
            tzinfo=timezone.utc,
        )
    )

    dt4 = Timestamp("2024-01-31 13:00:00")
    assert dt4 == snapshot(Timestamp("2024-01-31 13:00:00"))
"""
            }
        ),
    ).run_inline(
        ["--inline-snapshot=fix"], changed_files=snapshot({})
    ).run_inline(
        ["--inline-snapshot=update"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from pandas import Timestamp
from inline_snapshot import snapshot

from datetime import datetime
from datetime import timezone


def test_pandas_timestamp():
    dt = Timestamp("2024-01-31 13:00:00+0000", tz="UTC")
    assert dt == snapshot(datetime(2024, 1, 31, hour=13, tzinfo=timezone.utc))

    dt2 = Timestamp("2024-01-31 13:00:00")
    assert dt2 == snapshot(datetime(2024, 1, 31, hour=13))

    dt3 = Timestamp("2023-10-29 18:21:52.888000+0000", tz="UTC")
    assert dt3 == snapshot(
        datetime(
            2023,
            10,
            29,
            hour=18,
            minute=21,
            second=52,
            microsecond=888000,
            tzinfo=timezone.utc,
        )
    )

    dt4 = Timestamp("2024-01-31 13:00:00")
    assert dt4 == snapshot(datetime(2024, 1, 31, hour=13))
"""
            }
        ),
    ).run_inline()
