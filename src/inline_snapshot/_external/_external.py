from __future__ import annotations

import ast
import hashlib
import shutil
import typing
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from uuid import uuid4

from inline_snapshot._adapter.adapter import AdapterContext
from inline_snapshot._change import CallArg
from inline_snapshot._change import Replace
from inline_snapshot._external._format import get_format_handler
from inline_snapshot._external._format import get_format_handler_from_suffix
from inline_snapshot._external._outsource import Outsourced
from inline_snapshot._global_state import state
from inline_snapshot._inline_snapshot import create_snapshot
from inline_snapshot._unmanaged import declare_unmanaged

from .. import _config
from .._snapshot.generic_value import GenericValue
from ._external_location import ExternalLocation


class HashError(Exception):
    pass


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
        self._original_location = ExternalLocation.from_name(name)

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
                        (
                            ("fix" if self._original_location.stem else "create")
                            if self._value_changed
                            else "update"
                        ),
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

        if self._location.suffix is None:
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

        if not self._original_location.stem:
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

            return format.decode(f)
