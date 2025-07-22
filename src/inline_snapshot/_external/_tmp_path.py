from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

tmp_dir = TemporaryDirectory(prefix="inline-snapshot-")


def new_tmp_path(suffix: str) -> Path:
    return Path(tmp_dir.name) / f"tmp-path-{uuid4()}{suffix}"
