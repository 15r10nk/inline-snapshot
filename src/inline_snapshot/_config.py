from dataclasses import dataclass
from pathlib import Path

import toml


@dataclass
class Config:
    hash_length: int = 12


config = Config()


def read_config(path: Path) -> Config:
    if not path.exists():
        return Config()

    data = toml.loads(path.read_text("utf-8"))

    result = Config()

    try:
        config = data["tool"]["inline-snapshot"]
    except KeyError:
        pass
    else:
        try:
            result.hash_length = config["hash-length"]
        except KeyError:
            pass

    return result
