import os
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import List

import toml


@dataclass
class Config:
    hash_length: int = 12
    default_flags: List[str] = field(default_factory=lambda: ["short-report"])


config = Config()


def read_config(path: Path) -> Config:
    result = Config()
    if path.exists():

        data = toml.loads(path.read_text("utf-8"))

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

    env_var = "INLINE_SNAPSHOT_DEFAULT_FLAGS"
    if env_var in os.environ:
        result.default_flags = os.environ[env_var].split(",")

    return result
