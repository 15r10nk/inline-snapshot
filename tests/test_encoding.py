import pytest

from inline_snapshot._inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


@pytest.mark.parametrize(
    "encoding", ["utf-8", "windows-1251", "cp1252", "latin-1", "ascii"]
)
def test_encoding(encoding):

    special = ""
    for c in "aéЯÂþ":
        try:
            c.encode(encoding)
            special += c
        except UnicodeEncodeError:
            pass

    Example(
        f"""\
# -*- coding: {encoding} -*-

from inline_snapshot import snapshot

def test_a():
    assert "{special}"==snapshot()
""".encode(
            encoding
        )
    ).run_pytest(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "windows-1251": {
                    "tests/test_something.py": b'# -*- coding: windows-1251 -*-\n\nfrom inline_snapshot import snapshot\n\ndef test_a():\n    assert "a\xdf"==snapshot("a\xdf")\n'
                },
                "utf-8": {
                    "tests/test_something.py": """\
# -*- coding: utf-8 -*-

from inline_snapshot import snapshot

def test_a():
    assert "aéЯÂþ"==snapshot("aéЯÂþ")
"""
                },
                "cp1252": {
                    "tests/test_something.py": b'# -*- coding: cp1252 -*-\n\nfrom inline_snapshot import snapshot\n\ndef test_a():\n    assert "a\xe9\xc2\xfe"==snapshot("a\xe9\xc2\xfe")\n'
                },
                "latin-1": {
                    "tests/test_something.py": b'# -*- coding: latin-1 -*-\n\nfrom inline_snapshot import snapshot\n\ndef test_a():\n    assert "a\xe9\xc2\xfe"==snapshot("a\xe9\xc2\xfe")\n'
                },
                "ascii": {
                    "tests/test_something.py": """\
# -*- coding: ascii -*-

from inline_snapshot import snapshot

def test_a():
    assert "a"==snapshot("a")
"""
                },
            }
        )[encoding],
        returncode=snapshot(1),
        report=snapshot(
            {
                "utf-8": """\
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
These changes will be applied, because you used create\
""",
                "windows-1251": """\
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
These changes will be applied, because you used create\
""",
                "cp1252": """\
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
These changes will be applied, because you used create\
""",
                "latin-1": """\
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
These changes will be applied, because you used create\
""",
                "ascii": """\
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
These changes will be applied, because you used create\
""",
            }
        )[encoding],
    )
