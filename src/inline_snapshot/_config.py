import os
import sys
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional

if sys.version_info >= (3, 11):
    from tomllib import loads
else:
    from tomli import loads


@dataclass
class Config:
    hash_length: int = 12
    default_flags: List[str] = field(default_factory=lambda: ["short-report"])
    shortcuts: Dict[str, List[str]] = field(default_factory=dict)
    format_command: Optional[str] = None
    storage_dir: Optional[Path] = None


config = Config()


def read_config(path: Path) -> Config:
    result = Config()
    config = {}
    if path.exists():
        data = loads(path.read_text("utf-8"))

        try:
            config = data["tool"]["inline-snapshot"]
        except KeyError:
            pass

    try:
        result.hash_length = config["hash-length"]
    except KeyError:
        pass

    try:
        result.default_flags = config["default-flags"]
    except KeyError:
        pass

    result.shortcuts = config.get(
        "shortcuts", {"fix": ["create", "fix"], "review": ["review"]}
    )

    if storage_dir := config.get("storage-dir"):
        storage_dir = Path(storage_dir)
        if not storage_dir.is_absolute():
            # Make it relative to pyproject.toml, and absolute.
            storage_dir = path.parent.joinpath(storage_dir).absolute()
        result.storage_dir = storage_dir

    result.format_command = config.get("format-command", None)

    env_var = "INLINE_SNAPSHOT_DEFAULT_FLAGS"
    if env_var in os.environ:
        result.default_flags = os.environ[env_var].split(",")

    return result
