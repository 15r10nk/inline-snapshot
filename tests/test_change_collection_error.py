"""Tests for error handling during change collection in show_report()."""

import sys
from unittest.mock import patch

import pytest

from inline_snapshot import snapshot
from inline_snapshot._external._external import External
from inline_snapshot._external._external_file import ExternalFile
from inline_snapshot._inline_snapshot import SnapshotReference
from inline_snapshot.testing import Example
from tests.utils import path_transform


@pytest.mark.skipif(
    sys.platform != "linux",
    reason="test only on linux to prevent problems with path separators",
)
@pytest.mark.parametrize(
    "snapshot_type,expr",
    [
        (SnapshotReference, "snapshot()"),
        (External, "external()"),
        (ExternalFile, "external_file('test.txt')"),
    ],
)
def test_change_collection_error(expr, snapshot_type):
    """RuntimeError includes file and line from snapshot._expr when _changes() raises."""
    Example(
        f"""\
from inline_snapshot import snapshot,external,external_file

def test_a():
    assert "hello" == {expr}
"""
    ).run_inline(
        ["--inline-snapshot=report"],
        context_managers=[
            patch.object(
                snapshot_type,
                "_changes",
                side_effect=ValueError("simulated internal error"),
            )
        ],
        raises=path_transform(
            snapshot(
                {
                    "SnapshotReference": """\
RuntimeError:

error during change collection for snapshot (snapshot())
snapshot.
file: <tmp>/tests/test_something.py
line: 4
""",
                    "External": """\
AssertionError
RuntimeError:

error during change collection for snapshot (external("uuid:"))
snapshot.
file: <tmp>/tests/test_something.py
line: 4
""",
                    "ExternalFile": """\
AssertionError
RuntimeError:

error during change collection for snapshot (external_file('<tmp>/tests/test.txt'))
snapshot.
""",
                }
            )[snapshot_type.__name__]
        ),
    )
