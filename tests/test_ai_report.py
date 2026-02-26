"""Tests for --inline-snapshot=ai-report mode."""

from inline_snapshot import snapshot
from inline_snapshot.testing import Example


def test_ai_report_create():
    """ai-report with empty snapshot: shows source diff, nothing applied."""
    Example(
        """\
from inline_snapshot import snapshot

def test_a():
    assert "hello" == snapshot()
"""
    ).run_inline(
        ["--inline-snapshot=ai-report"],
        report=snapshot(
            """\
FAIL: your snapshot is missing one value.
If you just created this value with --inline-snapshot=create, the value is now \n\
created and you can ignore this message.
FAIL: some snapshots in this test have incorrect values.
If you just created this value with --inline-snapshot=create, the value is now \n\
created and you can ignore this message.

============================================================
inline-snapshot
============================================================
Pending create: 1 snapshot need updating.
Run: pytest --lf --inline-snapshot=create

[create] tests/test_something.py
  @@ -1,4 +1,4 @@
  \n\
   from inline_snapshot import snapshot
   \n\
   def test_a():
  -    assert "hello" == snapshot()
  +    assert "hello" == snapshot("hello")

============================================================

"""
        ),
        changed_files=snapshot({}),
    )


def test_ai_report_fix_apply():
    """fix+ai-report: applies fix, shows compact diff."""
    Example(
        """\
from inline_snapshot import snapshot

def test_a():
    assert 42 == snapshot(99)
"""
    ).run_inline(
        ["--inline-snapshot=fix,ai-report"],
        report=snapshot(
            """\
FAIL: some snapshots in this test have incorrect values.
If you just created this value with --inline-snapshot=create, the value is now \n\
created and you can ignore this message.

============================================================
inline-snapshot
============================================================
Applied fix: 1 snapshot.

[fix] tests/test_something.py
  @@ -1,4 +1,4 @@
  \n\
   from inline_snapshot import snapshot
   \n\
   def test_a():
  -    assert 42 == snapshot(99)
  +    assert 42 == snapshot(42)

Changes applied. Run: pytest --lf to verify.
============================================================

"""
        ),
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_a():
    assert 42 == snapshot(42)
"""
            }
        ),
    )


def test_ai_report_external_create():
    """external() with ai-report: shows source diff + external file content, nothing applied."""
    Example(
        """\
from inline_snapshot import outsource, snapshot

def test_a():
    assert outsource("hello world") == snapshot()
"""
    ).run_inline(
        ["--inline-snapshot=ai-report"],
        report=snapshot(
            """\
FAIL: your snapshot is missing one value.
If you just created this value with --inline-snapshot=create, the value is now \n\
created and you can ignore this message.
FAIL: some snapshots in this test have incorrect values.
If you just created this value with --inline-snapshot=create, the value is now \n\
created and you can ignore this message.

============================================================
inline-snapshot
============================================================
Pending create: 1 snapshot need updating.
Run: pytest --lf --inline-snapshot=create

[create] tests/test_something.py
  @@ -1,4 +1,6 @@
  \n\
   from inline_snapshot import outsource, snapshot
   \n\
  +from inline_snapshot import external
  +
   def test_a():
  -    assert outsource("hello world") == snapshot()
  +    assert outsource("hello world") == snapshot(external("uuid:f728b4fa-4248-4e3a-8a5d-2f346baa9455.txt"))

[create] uuid:f728b4fa-4248-4e3a-8a5d-2f346baa9455.txt
  hello world

============================================================

"""
        ),
        changed_files=snapshot({}),
    )


def test_ai_report_external_apply():
    """external() with create+ai-report: applies changes, shows diffs including file content."""
    Example(
        """\
from inline_snapshot import outsource, snapshot

def test_a():
    assert outsource("hello world") == snapshot()
"""
    ).run_inline(
        ["--inline-snapshot=create,ai-report"],
        report=snapshot(
            """\
FAIL: your snapshot is missing one value.
If you just created this value with --inline-snapshot=create, the value is now \n\
created and you can ignore this message.
FAIL: some snapshots in this test have incorrect values.
If you just created this value with --inline-snapshot=create, the value is now \n\
created and you can ignore this message.

============================================================
inline-snapshot
============================================================
Applied create: 1 snapshot.

[create] tests/test_something.py
  @@ -1,4 +1,6 @@
  \n\
   from inline_snapshot import outsource, snapshot
   \n\
  +from inline_snapshot import external
  +
   def test_a():
  -    assert outsource("hello world") == snapshot()
  +    assert outsource("hello world") == snapshot(external("uuid:f728b4fa-4248-4e3a-8a5d-2f346baa9455.txt"))

[create] uuid:f728b4fa-4248-4e3a-8a5d-2f346baa9455.txt
  hello world

Changes applied. Run: pytest --lf to verify.
============================================================

"""
        ),
        changed_files=snapshot(
            {
                "tests/__inline_snapshot__/test_something/test_a/f728b4fa-4248-4e3a-8a5d-2f346baa9455.txt": "hello world",
                "tests/test_something.py": """\
from inline_snapshot import outsource, snapshot

from inline_snapshot import external

def test_a():
    assert outsource("hello world") == snapshot(external("uuid:f728b4fa-4248-4e3a-8a5d-2f346baa9455.txt"))
""",
            }
        ),
    )
