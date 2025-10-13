import pytest

from inline_snapshot._inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


@pytest.mark.parametrize(
    "encoding", ["utf-8", "windows-1251", "cp1252", "latin-1", "ascii"]
)
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_encoding(encoding, newline):

    special = ""
    for c in "aéЯÂþ":
        try:
            c.encode(encoding)
            special += c
        except UnicodeEncodeError:
            pass

    code = f"""\
# -*- coding: {encoding} -*-

from inline_snapshot import snapshot

def test_a():
    assert "{special}"==snapshot()
"""

    fixed_code = code.replace("snapshot()", f'snapshot("{special}")').replace(
        "\n", newline
    )

    if encoding not in ("utf-8", "ascii"):
        fixed_code = fixed_code.encode(encoding)

    Example(code.replace("\n", newline).encode(encoding)).run_inline(
        ["--inline-snapshot=create"],
        changed_files={"tests/test_something.py": fixed_code},
        report=snapshot(
            {
                "utf-8": """\
FAIL: your snapshot is missing one value.
If you just created this value with --snapshot=create, the value is now created \n\
and you can ignore this message.
FAIL: some snapshots in this test have incorrect values.
If you just created this value with --snapshot=create, the value is now created \n\
and you can ignore this message.


═══════════════════════════════ inline-snapshot ════════════════════════════════
------------------------------- Create snapshots -------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -3,4 +3,4 @@                                                              |
|                                                                              |
|  from inline_snapshot import snapshot                                        |
|                                                                              |
|  def test_a():                                                               |
| -    assert "aéЯÂþ"==snapshot()                                              |
| +    assert "aéЯÂþ"==snapshot("aéЯÂþ")                                       |
+------------------------------------------------------------------------------+
These changes will be applied, because you used create

""",
                "windows-1251": """\
FAIL: your snapshot is missing one value.
If you just created this value with --snapshot=create, the value is now created \n\
and you can ignore this message.
FAIL: some snapshots in this test have incorrect values.
If you just created this value with --snapshot=create, the value is now created \n\
and you can ignore this message.


═══════════════════════════════ inline-snapshot ════════════════════════════════
------------------------------- Create snapshots -------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -3,4 +3,4 @@                                                              |
|                                                                              |
|  from inline_snapshot import snapshot                                        |
|                                                                              |
|  def test_a():                                                               |
| -    assert "aЯ"==snapshot()                                                 |
| +    assert "aЯ"==snapshot("aЯ")                                             |
+------------------------------------------------------------------------------+
These changes will be applied, because you used create

""",
                "cp1252": """\
FAIL: your snapshot is missing one value.
If you just created this value with --snapshot=create, the value is now created \n\
and you can ignore this message.
FAIL: some snapshots in this test have incorrect values.
If you just created this value with --snapshot=create, the value is now created \n\
and you can ignore this message.


═══════════════════════════════ inline-snapshot ════════════════════════════════
------------------------------- Create snapshots -------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -3,4 +3,4 @@                                                              |
|                                                                              |
|  from inline_snapshot import snapshot                                        |
|                                                                              |
|  def test_a():                                                               |
| -    assert "aéÂþ"==snapshot()                                               |
| +    assert "aéÂþ"==snapshot("aéÂþ")                                         |
+------------------------------------------------------------------------------+
These changes will be applied, because you used create

""",
                "latin-1": """\
FAIL: your snapshot is missing one value.
If you just created this value with --snapshot=create, the value is now created \n\
and you can ignore this message.
FAIL: some snapshots in this test have incorrect values.
If you just created this value with --snapshot=create, the value is now created \n\
and you can ignore this message.


═══════════════════════════════ inline-snapshot ════════════════════════════════
------------------------------- Create snapshots -------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -3,4 +3,4 @@                                                              |
|                                                                              |
|  from inline_snapshot import snapshot                                        |
|                                                                              |
|  def test_a():                                                               |
| -    assert "aéÂþ"==snapshot()                                               |
| +    assert "aéÂþ"==snapshot("aéÂþ")                                         |
+------------------------------------------------------------------------------+
These changes will be applied, because you used create

""",
                "ascii": """\
FAIL: your snapshot is missing one value.
If you just created this value with --snapshot=create, the value is now created \n\
and you can ignore this message.
FAIL: some snapshots in this test have incorrect values.
If you just created this value with --snapshot=create, the value is now created \n\
and you can ignore this message.


═══════════════════════════════ inline-snapshot ════════════════════════════════
------------------------------- Create snapshots -------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -3,4 +3,4 @@                                                              |
|                                                                              |
|  from inline_snapshot import snapshot                                        |
|                                                                              |
|  def test_a():                                                               |
| -    assert "a"==snapshot()                                                  |
| +    assert "a"==snapshot("a")                                               |
+------------------------------------------------------------------------------+
These changes will be applied, because you used create

""",
            }
        )[encoding],
    )
