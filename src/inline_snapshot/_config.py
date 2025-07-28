import sys
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional

from inline_snapshot._exceptions import UsageError

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
    format_command: str = ""
    storage_dir: Optional[Path] = None
    show_updates: bool = False
    tests_dir: Optional[Path] = None
    default_storage: str = "uuid"


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
        config.show_updates = tool_config["show-updates"]
    except KeyError:
        pass

    config.shortcuts = tool_config.get(
        "shortcuts", {"fix": ["create", "fix"], "review": ["review"]}
    )

    def read_path(name):
        result = tool_config.get(name)
        if result:
            result = Path(result)
            if not result.is_absolute():
                # Make it relative to pyproject.toml, and absolute.
                result = path.parent.joinpath(result).absolute()
        return result

    config.storage_dir = read_path("storage-dir")

    config.tests_dir = read_path("test-dir")

    if (
        config.tests_dir is None
        and path.exists()
        and (test_dir := path.parent / "tests").exists()
        and test_dir.is_dir()
    ):
        config.tests_dir = test_dir

    config.default_storage = tool_config.get("default-storage", "uuid")

    if config.default_storage not in ("uuid", "hash"):
        raise UsageError(
            f'default-storage has to be uuid or hash but is "{config.default_storage}"'
        )

    config.format_command = tool_config.get("format-command", "")

    return config
