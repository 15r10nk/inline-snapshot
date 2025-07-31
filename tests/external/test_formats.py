from inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


def test_json_format():

    Example(
        """\
from inline_snapshot import external

def test_a():
    assert [1,2] == external(".json")
    assert {"1":2} == external()
"""
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "tests/__inline_snapshot__/test_something/test_a/e3e70682-c209-4cac-a29f-6fbed82c07cd.json": """\
[
  1,
  2
]\
""",
                "tests/__inline_snapshot__/test_something/test_a/f728b4fa-4248-4e3a-8a5d-2f346baa9455.json": """\
{
  "1": 2
}\
""",
                "tests/test_something.py": """\
from inline_snapshot import external

def test_a():
    assert [1,2] == external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.json")
    assert {"1":2} == external("uuid:f728b4fa-4248-4e3a-8a5d-2f346baa9455.json")
""",
            }
        ),
    ).run_inline(
        ["--inline-snapshot=disable"]
    )


def test_binary_format():

    Example(
        """\
from inline_snapshot import external

def test_a():
    data=bytes(range(256))
    if False:
        data=data.replace(b"1",b"x")
    assert data == external()
"""
    ).run_pytest(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "tests/__inline_snapshot__/test_something/test_a/e3e70682-c209-4cac-a29f-6fbed82c07cd.bin": b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff",
                "tests/test_something.py": """\
from inline_snapshot import external

def test_a():
    data=bytes(range(256))
    if False:
        data=data.replace(b"1",b"x")
    assert data == external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.bin")
""",
            }
        ),
        report=snapshot(
            """\
------------------------------- Create snapshots -------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -4,4 +4,4 @@                                                              |
|                                                                              |
|      data=bytes(range(256))                                                  |
|      if False:                                                               |
|          data=data.replace(b"1",b"x")                                        |
| -    assert data == external()                                               |
| +    assert data ==                                                          |
| external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.bin")                    |
+------------------------------------------------------------------------------+
+--------------- uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.bin ----------------+
| 00000000: 0001 0203 0405 0607 0809 0a0b 0c0d 0e0f |................|         |
| 00000010: 1011 1213 1415 1617 1819 1a1b 1c1d 1e1f |................|         |
| 00000020: 2021 2223 2425 2627 2829 2a2b 2c2d 2e2f | !"#$%&'()*+,-./|         |
| 00000030: 3031 3233 3435 3637 3839 3a3b 3c3d 3e3f |0123456789:;<=>?|         |
| 00000040: 4041 4243 4445 4647 4849 4a4b 4c4d 4e4f |@ABCDEFGHIJKLMNO|         |
| 00000050: 5051 5253 5455 5657 5859 5a5b 5c5d 5e5f |PQRSTUVWXYZ[\\]^_|         |
| 00000060: 6061 6263 6465 6667 6869 6a6b 6c6d 6e6f |`abcdefghijklmno|         |
| 00000070: 7071 7273 7475 7677 7879 7a7b 7c7d 7e7f |pqrstuvwxyz{|}~.|         |
| 00000080: 8081 8283 8485 8687 8889 8a8b 8c8d 8e8f |................|         |
| 00000090: 9091 9293 9495 9697 9899 9a9b 9c9d 9e9f |................|         |
| 000000a0: a0a1 a2a3 a4a5 a6a7 a8a9 aaab acad aeaf |................|         |
| 000000b0: b0b1 b2b3 b4b5 b6b7 b8b9 babb bcbd bebf |................|         |
| 000000c0: c0c1 c2c3 c4c5 c6c7 c8c9 cacb cccd cecf |................|         |
| 000000d0: d0d1 d2d3 d4d5 d6d7 d8d9 dadb dcdd dedf |................|         |
| 000000e0: e0e1 e2e3 e4e5 e6e7 e8e9 eaeb eced eeef |................|         |
| 000000f0: f0f1 f2f3 f4f5 f6f7 f8f9 fafb fcfd feff |................|         |
+------------------------------------------------------------------------------+
These changes will be applied, because you used create\
"""
        ),
        returncode=1,
    ).change_code(
        lambda text: text.replace("False", "True") if isinstance(text, str) else text
    ).run_pytest(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "tests/__inline_snapshot__/test_something/test_a/e3e70682-c209-4cac-a29f-6fbed82c07cd.bin": b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f !\"#$%&'()*+,-./0x23456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff"
            }
        ),
        report=snapshot(
            """\
+--------------- uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.bin ----------------+
| @@ -1,7 +1,7 @@                                                              |
|                                                                              |
|  00000000: 0001 0203 0405 0607 0809 0a0b 0c0d 0e0f |................|        |
|  00000010: 1011 1213 1415 1617 1819 1a1b 1c1d 1e1f |................|        |
|  00000020: 2021 2223 2425 2627 2829 2a2b 2c2d 2e2f | !"#$%&'()*+,-./|        |
| -00000030: 3031 3233 3435 3637 3839 3a3b 3c3d 3e3f |0123456789:;<=>?|        |
| +00000030: 3078 3233 3435 3637 3839 3a3b 3c3d 3e3f |0x23456789:;<=>?|        |
|  00000040: 4041 4243 4445 4647 4849 4a4b 4c4d 4e4f |@ABCDEFGHIJKLMNO|        |
|  00000050: 5051 5253 5455 5657 5859 5a5b 5c5d 5e5f |PQRSTUVWXYZ[\\]^_|        |
|  00000060: 6061 6263 6465 6667 6869 6a6b 6c6d 6e6f |`abcdefghijklmno|        |
+------------------------------------------------------------------------------+
These changes will be applied, because you used fix\
"""
        ),
        returncode=1,
    )


def test_large_binary_format():

    Example(
        """\
from inline_snapshot import external

def test_a():
    data=bytes(range(256))*20
    assert data == external()
"""
    ).run_pytest(
        ["--inline-snapshot=create"],
        report=snapshot(
            """\
------------------------------- Create snapshots -------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -2,4 +2,4 @@                                                              |
|                                                                              |
|                                                                              |
|  def test_a():                                                               |
|      data=bytes(range(256))*20                                               |
| -    assert data == external()                                               |
| +    assert data ==                                                          |
| external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.bin")                    |
+------------------------------------------------------------------------------+
+--------------- uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.bin ----------------+
| <binary file (5120 bytes)>                                                   |
+------------------------------------------------------------------------------+
These changes will be applied, because you used create\
"""
        ),
        returncode=1,
    )


def test_unknown_format():

    Example(
        {
            "test.blub": "hi",
            "test_a.py": """\
from inline_snapshot import external_file

def test_a():
    assert "hi" == external_file("test.blub")
""",
        }
    ).run_pytest(
        ["--inline-snapshot=create"],
        error=snapshot(
            """\
>       assert "hi" == external_file("test.blub")
>           raise UsageError(f"Format '{suffix}' is unknown.")
E           inline_snapshot._exceptions.UsageError: Format '.blub' is unknown.
"""
        ),
        returncode=snapshot(1),
    )


def test_replace_format():

    Example(
        {
            "test.blub": "hi",
            "test_a.py": """\
from pathlib import Path
from inline_snapshot import external_file,register_format,TextDiff,Format

@register_format(replace_handler=True)
class BytesFormat(TextDiff, Format[bytes]):
    suffix=".bin"

    def handle(self, data: object):
        return isinstance(data, bytes)

    def encode(self, value: bytes, path: Path):
        path.write_text(repr(value))

    def decode(self, path: Path) -> bytes:
        return eval(path.read_text())

def test_a():
    assert b"hi\\nyou" == external_file("test.bin")
""",
        }
    ).run_pytest(
        ["--inline-snapshot=create"],
        changed_files=snapshot({"test.bin": "b'hi\\nyou'"}),
        returncode=snapshot(1),
    ).run_inline()


def test_replace_format_error():

    Example(
        {
            "test.blub": "hi",
            "test_a.py": """\
from pathlib import Path
from inline_snapshot import external_file,register_format,TextDiff,Format

@register_format
class BytesFormat(TextDiff, Format[bytes]):
    suffix=".bin"
    ...
""",
        }
    ).run_pytest(
        error=snapshot(
            "E   inline_snapshot._exceptions.UsageError: A format handler is already registered for the suffix '.bin'.\n"
        ),
        returncode=snapshot(2),
    )


def test_multiple_handler_found():

    Example(
        {
            "test.blub": "hi",
            "test_a.py": """\
from pathlib import Path
from inline_snapshot import external,register_format,TextDiff,Format

@register_format
class BytesFormat(TextDiff, Format[bytes]):
    suffix=".bin2"

    def is_format_for(self,value):
        return isinstance(value,bytes)

def test_a():
    assert b"bytes" == external()
""",
        }
    ).run_pytest(
        error=snapshot(
            """\
>       assert b"bytes" == external()
>           raise UsageError(
E           inline_snapshot._exceptions.UsageError: Multiple format handlers found for the given type 'bytes'. The following handlers have the same priority: ['.bin', '.bin2']. You can explicitly choose one with external('.suffix') or adjust the priorities of the handlers if you implemented them.
"""
        ),
        returncode=snapshot(1),
    )
