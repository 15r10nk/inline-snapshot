import os
import sys
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Dict
from typing import List


if sys.version_info >= (3, 11):
    from tomllib import loads
else:
    from tomli import loads


@dataclass
class Config:
    hash_length: int = 12
    default_flags: List[str] = field(default_factory=lambda: ["short-report"])
    shortcuts: Dict[str, List[str]] = field(default_factory=dict)


config = Config()


def read_config(path: Path) -> Config:
    result = Config()
    if path.exists():

        data = loads(path.read_text("utf-8"))

        try:
            config = data["tool"]["inline-snapshot"]
        except KeyError:
            pass
        else:
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

    env_var = "INLINE_SNAPSHOT_DEFAULT_FLAGS"
    if env_var in os.environ:
        result.default_flags = os.environ[env_var].split(",")

    return result
