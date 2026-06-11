from __future__ import annotations

import os
from pathlib import Path

from inline_snapshot._global_state import state


def external_files_list_path() -> Path:
    storage_dir = state().config.storage_dir
    assert storage_dir is not None
    return storage_dir / "files_using_external.txt"


def external_files_base_dir() -> Path:
    path = external_files_list_path()
    return path.parent.parent.resolve()


def read_external_source_files() -> set[Path]:
    result: set[Path] = set()

    path = external_files_list_path()
    base_dir = external_files_base_dir()
    if not path.exists():
        return result

    for line in path.read_text("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith(("#", "<<<<<<<", "=======", ">>>>>>>")):
            continue

        file = Path(line)
        assert not file.is_absolute(), file
        file = base_dir / file

        if not file.exists():
            continue

        result.add(file.resolve())

    return result


def write_external_source_files(files: set[Path]):
    path = external_files_list_path()

    if not files:
        if path.exists():
            path.unlink()
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    base_dir = external_files_base_dir()

    def to_text(file: Path) -> str:
        resolved = file.resolve()
        try:
            return resolved.relative_to(base_dir).as_posix()
        except ValueError:
            try:
                return Path(os.path.relpath(resolved, base_dir)).as_posix()
            except ValueError:
                return resolved.as_posix()

    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("".join(f"{to_text(file)}\n" for file in sorted(files)))
