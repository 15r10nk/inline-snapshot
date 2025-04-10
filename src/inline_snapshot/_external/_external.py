from __future__ import annotations

import ast
import hashlib
import re
import shutil
import typing
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Generator
from uuid import uuid4

from inline_snapshot import UsageError
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

        format = get_format_handler(data, self._location.suffix)
        if suffix is None:
            suffix = format.suffix
        self._location.suffix = suffix

        storage = state().storage
        assert storage

        with storage.store(self._location) as f:
            format.encode(data, f)

    def __eq__(self, other):
        if isinstance(other, GenericValue):
            return NotImplemented

        if isinstance(other, Outsourced):
            return self.data == other.data

        return NotImplemented

    def __repr__(self) -> str:
        return f'external("{self._location.to_str()}")'

    def _load_value(self) -> Any:
        return self.data


def outsource(data, suffix: str | None = None):
    if suffix and suffix[0] != ".":
        raise ValueError("suffix has to start with a '.' like '.png'")

    if not state().active:
        return data

    return Outsourced(data, suffix)


class Protocol:

    @contextmanager
    def load(self, location: ExternalLocation) -> Generator[typing.BinaryIO]:
        raise NotImplementedError

    @contextmanager
    def store(self, location: ExternalLocation) -> Generator[typing.BinaryIO]:
        raise NotImplementedError


def file_digest(file: typing.BinaryIO, name: str):
    algo = hashlib.new(name)
    algo.update(file.read())
    return algo


class DiscStorage(Protocol):
    def __init__(self, directory):
        self.directory = Path(directory)

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
        gitignore = self.directory / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text(
                "# ignore all snapshots which are not referred in the source\n*-new.*\n",
                "utf-8",
            )

    @contextmanager
    def load(self, location: ExternalLocation) -> Generator[typing.BinaryIO]:
        path = self._lookup_path(location.path)
        with path.open("rb") as f:
            yield f

    @contextmanager
    def store(self, location: ExternalLocation) -> Generator[typing.BinaryIO]:
        self._ensure_directory()

        tmp_name = self.directory / str(uuid4())

        with tmp_name.open("wb") as f:
            yield f

        with tmp_name.open("rb") as f:
            hash_name = file_digest(f, "sha256").hexdigest()

        location.storage = "hash"

        location.stem = hash_name

        assert location.suffix is not None
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


def external(name: str | None = None):
    return create_snapshot(External, name)


def get_format_handler(data, suffix: str | None) -> type[Format]:

    for formatter in all_formats:
        if formatter.handle(data) and (
            suffix == formatter.suffix
            if formatter.suffix_required
            else (suffix is None or suffix == formatter.suffix)
        ):
            return formatter
    else:
        raise UsageError("data has to be of type bytes | str")

    return format


def get_format_handler_from_suffix(suffix: str) -> type[Format] | None:
    for formatter in all_formats:
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
        format = get_format_handler(other, self._location.suffix)

        self._location.suffix = format.suffix

        storage = state().storage
        with storage.store(self._location) as f:
            format.encode(other, f)
        self._value_changed = True

    def __eq__(self, other):
        """Two external objects are equal if they have the same value"""

        if isinstance(other, Outsourced):
            self._location.suffix = other._location.suffix
            other = other.data

        if self._location.stem is None:
            if state().update_flags.create:
                self._assign(other)
                state().missing_values += 1
                return True
            return False

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

        with storage.load(location) as f:
            format = get_format_handler_from_suffix(location.suffix)
            if format is None:
                raise ValueError(f"format {location.suffix} is unknown")

            return format.decode(f, None)


class Format:

    suffix: str | None

    suffix_required = False

    @staticmethod
    def handle(data):
        raise NotImplementedError

    @staticmethod
    def encode(value, file):
        raise NotImplementedError

    @staticmethod
    def decode(file, meta):
        raise NotImplementedError


all_formats = []


def register_format(cls):
    all_formats.append(cls)
    return cls


@register_format
class BinFormat(Format):
    suffix = ".bin"

    @staticmethod
    def handle(data):
        return isinstance(data, bytes)

    @staticmethod
    def encode(value: bytes, file: typing.BinaryIO):
        file.write(value)

    @staticmethod
    def decode(file: typing.BinaryIO, meta) -> bytes:
        return file.read()


@register_format
class TxtFormat(Format):
    suffix = ".txt"

    @staticmethod
    def handle(data):
        return isinstance(data, str)

    @staticmethod
    def encode(value: str, file: typing.BinaryIO):
        file.write(value.encode("utf-8"))

    @staticmethod
    def decode(file: typing.BinaryIO, meta) -> str:
        return file.read().decode("utf-8")


def txt_like_suffix(suffix):
    @register_format
    class NewFormat(Format):

        suffix_required = True

        @staticmethod
        def handle(data):
            return isinstance(data, str)

        @staticmethod
        def encode(value: str, file: typing.BinaryIO):
            file.write(value.encode("utf-8"))

        @staticmethod
        def decode(file: typing.BinaryIO, meta) -> str:
            return file.read().decode("utf-8")

    NewFormat.suffix = suffix
