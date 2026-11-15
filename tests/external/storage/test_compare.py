from hashlib import sha256

import pytest
from dirty_equals import IsStr


@pytest.mark.parametrize("flags", ["report", "disable"])
@pytest.mark.parametrize(
    "backend, actual", [("FileStorage", "stored"), ("CasefoldStorage", "STORED")]
)
def test_compare_stored_document(storage_example, flags, backend, actual):
    storage_example(
        {
            ".inline-snapshot/custom/value.txt": "stored",
            "tests/test_something.py": f"""\
import json
from inline_snapshot import external, get_snapshot_value

def test_document():
    expected = external("custom:value.txt")
    assert expected == {actual!r}
    assert {actual!r} == expected
    assert not (expected != {actual!r})
    assert json.dumps(get_snapshot_value(expected)) == '"stored"'
""",
        },
        backend=backend,
    ).run_pytest(
        [f"--inline-snapshot={flags}"], outcomes={"passed": 1}, changed_files={}
    )


@pytest.mark.parametrize("flags", ["report", "disable"])
@pytest.mark.parametrize(
    "backend, actual", [("FileStorage", "stored"), ("CasefoldStorage", "STORED")]
)
def test_comparison_does_not_require_an_encoder(
    storage_example, flags, backend, actual
):
    storage_example(
        {
            ".inline-snapshot/custom/value.readonly": "stored",
            "tests/test_something.py": f"""\
from inline_snapshot import Format, TextDiff, external, register_format

@register_format
class ReadOnlyText(TextDiff, Format[str]):
    suffix = ".readonly"

    def is_format_for(self, value):
        return isinstance(value, str)

    def decode(self, path):
        return path.read_text()

    def encode(self, value, path):
        raise OSError("this format supports reading existing snapshots only")

def test_document():
    assert {actual!r} == external("custom:value.readonly")
""",
        },
        backend=backend,
    ).run_pytest(
        [f"--inline-snapshot={flags}"], outcomes={"passed": 1}, changed_files={}
    )


@pytest.mark.parametrize("flags", ["report", "disable"])
def test_digest_comparison_does_not_download_snapshot(storage_example, flags):
    digest = sha256(b"stored").hexdigest()
    storage_example(
        {
            "tests/test_something.py": f"""\
from inline_snapshot import external

def test_document():
    assert "stored" == external("digest:{digest}.txt")
""",
        },
        name="digest",
        backend="OfflineDigestStorage",
    ).run_pytest(
        [f"--inline-snapshot={flags}"], outcomes={"passed": 1}, changed_files={}
    )


def test_update_content_addressed_snapshot(storage_example):
    old_digest = sha256(b"stored").hexdigest()
    new_digest = sha256(b"changed").hexdigest()
    original_test = f"""\
from inline_snapshot import external

def test_document():
    assert "changed" == external("digest:{old_digest}.txt")
"""
    storage_example(
        {
            f".inline-snapshot/digest/{old_digest}.txt": "stored",
            "tests/test_something.py": original_test,
        },
        name="digest",
        backend="DigestStorage",
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files={
            f".inline-snapshot/digest/{new_digest}.txt": "changed",
            "tests/test_something.py": original_test.replace(old_digest, new_digest),
        },
    ).run_pytest(
        ["--inline-snapshot=disable"], outcomes={"passed": 1}, changed_files={}
    )


@pytest.mark.parametrize("flags", ["report", "disable"])
def test_cannot_compare_two_external_snapshots(storage_example, flags):
    storage_example(
        {
            "tests/test_something.py": """\
import pytest
from inline_snapshot import UsageError, external

def test_document():
    with pytest.raises(UsageError, match="you cannot compare external"):
        external("custom:first.txt") == external("custom:second.txt")
""",
        },
        backend="CasefoldStorage",
    ).run_pytest(
        [f"--inline-snapshot={flags}"], outcomes={"passed": 1}, changed_files={}
    )


def test_disabled_comparison_reports_mismatch(storage_example):
    storage_example(
        {
            ".inline-snapshot/custom/value.txt": "stored",
            "tests/test_something.py": """\
from inline_snapshot import external

def test_document():
    assert "different" == external("custom:value.txt")
""",
        },
        backend="CasefoldStorage",
    ).run_pytest(
        ["--inline-snapshot=disable"],
        returncode=1,
        outcomes={"failed": 1},
        error=IsStr(
            regex=r'(?s).*assert .*different.*external\("custom:value.txt"\).*'
        ),
        changed_files={},
    )


def test_extract_missing_snapshot_value(storage_example):
    storage_example(
        {
            "tests/test_something.py": """\
from inline_snapshot import external, get_snapshot_value

def test_document():
    assert get_snapshot_value(external("custom:missing.txt")) is ...
""",
        },
        backend="CasefoldStorage",
    ).run_pytest(
        ["--inline-snapshot=disable"], outcomes={"passed": 1}, changed_files={}
    )


def test_update_snapshot_from_one_shot_iterator(storage_example):
    old_digest = sha256(b"stored").hexdigest()
    new_digest = sha256(b"one\ntwo").hexdigest()
    source = f"""\
from collections.abc import Iterator
from inline_snapshot import Format, TextDiff, external, register_format

@register_format
class Lines(TextDiff, Format[Iterator[str]]):
    suffix = ".lines"

    def is_format_for(self, value):
        return isinstance(value, Iterator)

    def encode(self, value, path):
        with path.open("w", encoding="utf-8", newline="\\n") as stream:
            stream.write("\\n".join(value))

    def decode(self, path):
        return iter(path.read_text().splitlines())

def test_document():
    assert iter(["one", "two"]) == external("digest:{old_digest}.lines")
"""
    storage_example(
        {
            f".inline-snapshot/digest/{old_digest}.lines": "stored",
            "tests/test_something.py": source,
        },
        name="digest",
        backend="DigestStorage",
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files={
            f".inline-snapshot/digest/{new_digest}.lines": "one\ntwo",
            "tests/test_something.py": source.replace(old_digest, new_digest),
        },
    ).run_pytest(
        ["--inline-snapshot=disable"], outcomes={"passed": 1}, changed_files={}
    )
