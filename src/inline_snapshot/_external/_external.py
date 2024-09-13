from __future__ import annotations

import ast
import hashlib
import json
import re
import shutil
import typing
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Generator
from uuid import uuid4

from inline_snapshot._adapter.adapter import AdapterContext
from inline_snapshot._change import CallArg
from inline_snapshot._change import Replace
from inline_snapshot._global_state import state
from inline_snapshot._inline_snapshot import create_snapshot
from inline_snapshot._unmanaged import declare_unmanaged

from .. import _config
from .._snapshot.generic_value import GenericValue


class HashError(Exception):
    pass


@dataclass()
class ExternalLocation:
    storage: str | None
    stem: str | None
    suffix: str | None

    @classmethod
    def from_name(cls, name: str | None):
        if name is None:
            return cls(None, None, None)

        m = re.fullmatch(r"([0-9a-fA-F]*)\*?(\.[a-zA-Z0-9]*)", name)

        if m:
            storage = "hash"
            path = name
        elif ":" in name:
            storage, path = name.split(":", 1)
        else:
            raise ValueError(
                "path has to be of the form <hash>.<suffix> or <partial_hash>*.<suffix>"
            )
        if "." in path:
            stem, suffix = path.split(".", 1)
            suffix = "." + suffix
        else:
            stem = path
            suffix = None

        return cls(storage, stem, suffix)

    @property
    def path(self) -> str:
        return f"{self.stem}{self.suffix or ''}"

    def to_str(self) -> str:
        return f"{self.storage}:{self.path}"


class Outsourced:
    def __init__(self, data: Any, suffix: str | None):
        self.data = data
        self._location = ExternalLocation("hash", None, suffix)

        format = get_format_handler(data, self._location)
        if suffix is None:
            suffix = format.suffix
        self._location.suffix = suffix
        meta_data = {"format_handler": format.__name__}

        storage = state().storage
        assert storage

        with storage.store(self._location, meta_data) as f:
            format.encode(data, f)

    def __eq__(self, other):
        if isinstance(other, GenericValue):
            return NotImplemented

        if isinstance(other, Outsourced):
            return self.data == other.data

        return self.data == other

    def __repr__(self) -> str:
        return f'external("{self._location.to_str()}")'

    def _load_value(self) -> Any:
        return self.data


def outsource(data, suffix: str | None = None):

    if suffix and suffix[0] != ".":
        raise ValueError("suffix has to start with a '.' like '.png'")

    return Outsourced(data, suffix)


class Protocol:

    @contextmanager
    def load(
        self, location: ExternalLocation
    ) -> Generator[tuple[typing.BinaryIO, Any]]:
        raise NotImplementedError

    @contextmanager
    def store(
        self, location: ExternalLocation, metadata: Any
    ) -> Generator[typing.BinaryIO]:
        raise NotImplementedError


def file_digest(file: typing.BinaryIO, name: str):
    algo = hashlib.new(name)
    algo.update(file.read())
    return algo


class DiscStorage(Protocol):
    def __init__(self, directory):
        self.directory = Path(directory)

    @property
    def metadata_directory(self):
        return self.directory / ".." / "metadata"

    def add(self, data, suffix=None):
        # for testing only
        self._ensure_directory()

        if suffix is None:
            suffix = ".txt" if isinstance(data, str) else ".bin"

        if isinstance(data, str):
            data = data.encode()

        tmp_name = self.directory / str(uuid4())

        with tmp_name.open("wb") as f:
            f.write(data)

        with tmp_name.open("rb") as f:
            hash_name = file_digest(f, "sha256").hexdigest()

        shutil.move(tmp_name, self.directory / (hash_name + suffix))

    def _ensure_directory(self):
        self.directory.mkdir(exist_ok=True, parents=True)
        self.metadata_directory.mkdir(exist_ok=True, parents=True)
        gitignore = self.directory / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text(
                "# ignore all snapshots which are not referred in the source\n*-new.*\n",
                "utf-8",
            )

    def save(self, name, data):
        assert "*" not in name
        self._ensure_directory()
        (self.directory / name).write_bytes(data)

    @contextmanager
    def load(
        self, location: ExternalLocation
    ) -> Generator[tuple[typing.BinaryIO, Any]]:
        path = self._lookup_path(location.path)
        metadata_path = self._metadata_path(location.path)
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text())
        else:
            metadata = {"format_handler": "LegacyFormat"}
        with path.open("rb") as f:
            yield f, metadata

    @contextmanager
    def store(
        self, location: ExternalLocation, metadata: Any
    ) -> Generator[typing.BinaryIO]:
        self._ensure_directory()

        if location.stem is not None:
            try:
                self._lookup_path(location.path)
            except:
                pass
            else:
                return

        tmp_name = self.directory / str(uuid4())

        with tmp_name.open("wb") as f:
            yield f

        with tmp_name.open("rb") as f:
            hash_name = file_digest(f, "sha256").hexdigest()

        location.storage = "hash"

        location.stem = hash_name

        metadata_path = self.metadata_directory / Path(location.path + ".json")

        assert location.suffix is not None
        metadata_path.write_text(json.dumps(metadata))
        if (self.directory / (hash_name + location.suffix)).exists():
            tmp_name.unlink()
        else:
            shutil.move(
                tmp_name, self.directory / (hash_name + "-new" + location.suffix)
            )

        path = hash_name[: _config.config.hash_length]

        if _config.config.hash_length < len(hash_name):
            path += "*"

        location.stem = path

    def read(self, name):
        return self._lookup_path(name).read_bytes()

    def prune_new_files(self):
        for file in self.directory.glob("*-new.*"):
            file.unlink()

    def list(self) -> set[str]:

        if self.directory.exists():
            return {item.name for item in self.directory.iterdir()} - {".gitignore"}
        else:
            return set()

    def persist(self, name):
        try:
            file = self._lookup_path(name)
        except HashError:
            return
        if file.stem.endswith("-new"):
            stem = file.stem[:-4]
            file.rename(file.with_name(stem + file.suffix))

    def _metadata_path(self, name):
        path = self._lookup_path(name)
        path = Path(str(path) + ".json")
        return self.metadata_directory / path.name

    def _lookup_path(self, name) -> Path:
        if "*" not in name:
            p = Path(name)
            name = p.stem + "*" + p.suffix
        files = list(self.directory.glob(name))

        if len(files) > 1:
            raise HashError(f"hash collision files={sorted(f.name for f in  files)}")

        if not files:
            raise HashError(f"hash {name!r} is not found in the DiscStorage")

        return files[0]

    def lookup_all(self, name) -> set[str]:
        return {file.name for file in self.directory.glob(name)}

    def remove(self, name):
        self._lookup_path(name).unlink()


DiscStorage = DiscStorage


class UuidStorage: ...


def external(name: str | None = None):
    return create_snapshot(External, name)


def parse_external_path(name):
    m = re.fullmatch(r"([0-9a-fA-F]*)\*?(\.[a-zA-Z0-9]*)", name)

    if m:
        _storage = "hash"
        _filename = name
    elif ":" in name:
        _storage, _filename = name.split(":", 1)
    else:
        raise ValueError(
            "path has to be of the form <hash>.<suffix> or <partial_hash>*.<suffix>"
        )
    return _storage, _filename


def get_format_handler(data, location: ExternalLocation) -> type[Format]:
    suffix = location.suffix

    for formatter in all_formats():
        if formatter.handle_type(type(data)):
            suffix = formatter.suffix
            format = formatter
            break
    else:
        raise TypeError("data has to be of type bytes | str")

    if not suffix or suffix[0] != ".":
        raise ValueError("suffix has to start with a '.' like '.png'")
    else:
        format = get_format_handler_from_suffix(suffix)
        if format is None:
            raise TypeError("data has to be of type bytes | str")

    return format


def get_format_handler_from_suffix(suffix: str) -> type[Format] | None:
    for formatter in all_formats():
        if formatter.suffix == suffix:
            return formatter
    return None


@declare_unmanaged
class External:
    def __init__(self, name: str, expr, context: AdapterContext):
        """External objects are used as a representation for outsourced data.
        You should not create them directly.

        The external data is by default stored inside `<pytest_config_dir>/.inline-snapshot/external`,
        where `<pytest_config_dir>` is replaced by the directory containing the Pytest configuration file, if any.
        To store data in a different location, set the `storage-dir` option in pyproject.toml.
        Data which is outsourced but not referenced in the source code jet has a '-new' suffix in the filename.

        Parameters:
            name: the name of the external stored object.
        """
        self._expr = expr
        self._context = context
        self._original_name = name

        self._location = ExternalLocation.from_name(name)

        self._value_changed = False

    def result(self):
        return self

    @classmethod
    def create_raw(cls, obj):
        return cls._load_value_from_location(ExternalLocation.from_name(obj))

    # try:
    #     return cls._load_value_from_location(ExternalLocation.from_name(obj))
    # except HashError:
    #     return MissingExternalObject(obj)

    def _changes(self):
        if self._expr is None:
            node = None
        else:
            node = self._expr.node
            assert isinstance(node, ast.Call)
        new_name = self._location.to_str()
        if new_name != self._original_name:
            if self._original_name is None:
                return [
                    CallArg(
                        "create",
                        self._context.file,
                        node,
                        0,
                        None,
                        f'"{new_name}"',
                        new_name,
                    )
                ]
            else:
                return [
                    Replace(
                        "fix" if self._value_changed else "update",
                        self._context.file,
                        node.args[0] if node else None,
                        f'"{new_name}"',
                        self._original_name,
                        new_name,
                    )
                ]
        else:
            return []

    def __repr__(self):
        """Returns the representation of the external object.

        The length of the hash can be specified in the
        [config](configuration.md).
        """

        return f'external("{self._location.to_str()}")'

    def _assign(self, other):
        format = get_format_handler(other, self._location)

        self._location.suffix = format.suffix

        storage = state().storage
        with storage.store(self._location, None) as f:
            format.encode(other, f)
        self._value_changed = True

    def __eq__(self, other):
        """Two external objects are equal if they have the same hash and
        suffix."""

        if self._location.stem is None:
            self._assign(other)
            state().missing_values += 1
            return True

        if isinstance(other, Outsourced):
            other = other.data
        if isinstance(other, External):
            other = other._load_value()

        if isinstance(other, GenericValue):
            return NotImplemented

        if self._location.stem:
            value = self._load_value()
            result = value == other
        else:
            result = False
            state().missing_values += 1

        if state().update_flags.fix or state().update_flags.update:
            if not result:
                self._assign(other)
                state().incorrect_values += 1
            return True

        return result

    def _load_value(self):
        return self._load_value_from_location(self._location)

    @classmethod
    def _load_value_from_location(cls, location):
        storage = state().storage
        assert storage is not None

        with storage.load(location) as (f, metadata):
            format_name = metadata["format_handler"]
            for format in all_formats():
                if format.__name__ == format_name:
                    break
            else:
                raise ValueError(f"format {format_name} is unknown")

            return format.decode(f, None)


# outsource(data,suffix=".json",storage="hash",path="some/local/path")
class Format:

    suffix: str | None

    @staticmethod
    def handle_type(data_type):
        raise NotImplementedError

    @staticmethod
    def encode(value, file):
        raise NotImplementedError

    @staticmethod
    def decode(file, meta):
        raise NotImplementedError


class LegacyFormat(Format):
    suffix = None

    @staticmethod
    def handle_type(data_type):
        # this format is only used for loading
        return False

    @staticmethod
    def encode(value: bytes, file: typing.BinaryIO):
        assert False
        file.write(value)

    @staticmethod
    def decode(file: typing.BinaryIO, meta) -> LegacyType:

        return LegacyType(file.read())


class LegacyType:
    def __init__(self, data):
        self.data = data

    def __eq__(self, other):
        if isinstance(other, Outsourced):
            return NotImplemented
        if isinstance(other, str):
            other = other.encode("utf-8")
        return self.data == other


class MissingExternalObject:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return False

    def __repr__(self):
        return f"MissingExternalObject({self.name})"


class BinFormat(Format):
    suffix = ".bin"

    @staticmethod
    def handle_type(data_type):
        return data_type is bytes

    @staticmethod
    def encode(value: bytes, file: typing.BinaryIO):
        file.write(value)

    @staticmethod
    def decode(file: typing.BinaryIO, meta) -> bytes:
        return file.read()


class TxtFormat(Format):
    suffix = ".txt"

    @staticmethod
    def handle_type(data_type):
        return data_type is str

    @staticmethod
    def encode(value: str, file: typing.BinaryIO):
        file.write(value.encode("utf-8"))

    @staticmethod
    def decode(file: typing.BinaryIO, meta) -> str:
        return file.read().decode("utf-8")


def all_formats():
    return Format.__subclasses__()
