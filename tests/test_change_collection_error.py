"""Tests for error handling during change collection in show_report()."""

import sys
from unittest.mock import patch

import pytest

from inline_snapshot import snapshot
from inline_snapshot._external._external import ExternalData
from inline_snapshot._external._external_file import ExternalFileData
from inline_snapshot._snapshot.snapshot_data import SnapshotData
from inline_snapshot.testing import Example
from tests.utils import path_transform


@pytest.mark.skipif(
    sys.platform != "linux",
    reason="test only on linux to prevent problems with path separators",
)
@pytest.mark.parametrize(
    "snapshot_type,expr",
    [
        (SnapshotData, "snapshot()"),
        (ExternalData, "external()"),
        (ExternalFileData, "external_file('test.txt')"),
    ],
)
def test_change_collection_error(expr, snapshot_type):
    """RuntimeError includes file and line from snapshot._expr when _changes() raises."""
    Example(f"""\
from inline_snapshot import snapshot,external,external_file

def test_a():
    assert "hello" == {expr}
""").run_inline(
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
                    "SnapshotData": """\
RuntimeError:

error during change collection for snapshot (snapshot(...))
snapshot.
""",
                    "ExternalData": """\
AssertionError
RuntimeError:

error during change collection for snapshot (external("uuid:"))
snapshot.
""",
                    "ExternalFileData": """\
AssertionError
RuntimeError:

error during change collection for snapshot (external_file('test.txt'))
snapshot.
""",
                }
            )[snapshot_type.__name__]
        ),
        reported_categories=set(),
    )
