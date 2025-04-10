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
    default_flags_tui: List[str] = field(default_factory=lambda: ["short-report"])
    shortcuts: Dict[str, List[str]] = field(default_factory=dict)
    format_command: Optional[str] = None
    storage_dir: Optional[Path] = None
    skip_snapshot_updates_for_now: bool = False


config = Config()


def read_config(path: Path, config=Config()) -> Config:
    tool_config = {}

    if path.exists():
        data = loads(path.read_text("utf-8"))

        try:
            tool_config = data["tool"]["inline-snapshot"]
        except KeyError:
            pass

    try:
        config.hash_length = tool_config["hash-length"]
    except KeyError:
        pass

    try:
        config.default_flags = tool_config["default-flags"]
    except KeyError:
        pass

    try:
        config.default_flags_tui = tool_config["default-flags-tui"]
    except KeyError:
        pass

    try:
        config.skip_snapshot_updates_for_now = tool_config[
            "skip-snapshot-updates-for-now"
        ]
    except KeyError:
        pass

    config.shortcuts = tool_config.get(
        "shortcuts", {"fix": ["create", "fix"], "review": ["review"]}
    )

    if storage_dir := tool_config.get("storage-dir"):
        storage_dir = Path(storage_dir)
        if not storage_dir.is_absolute():
            # Make it relative to pyproject.toml, and absolute.
            storage_dir = path.parent.joinpath(storage_dir).absolute()
        config.storage_dir = storage_dir

    config.format_command = tool_config.get("format-command", None)

    return config
