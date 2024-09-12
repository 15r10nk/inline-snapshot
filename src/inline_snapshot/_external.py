import hashlib
import pathlib
import re
from typing import Optional
from typing import Set
from typing import Union

from . import _config
from ._global_state import state
from ._snapshot.generic_value import GenericValue


class HashError(Exception):
    pass


class HashStorage:
    def __init__(self, directory):
        self.directory = pathlib.Path(directory)

    def _ensure_directory(self):
        self.directory.mkdir(exist_ok=True, parents=True)
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

    def read(self, name):
        return self._lookup_path(name).read_bytes()

    def prune_new_files(self):
        for file in self.directory.glob("*-new.*"):
            file.unlink()

    def list(self) -> Set[str]:
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

    def _lookup_path(self, name) -> pathlib.Path:
        if "*" not in name:
            p = pathlib.Path(name)
            name = p.stem + "*" + p.suffix
        files = list(self.directory.glob(name))

        if len(files) > 1:
            raise HashError(f"hash collision files={sorted(f.name for f in  files)}")

        if not files:
            raise HashError(f"hash {name!r} is not found in the HashStorage")

        return files[0]

    def lookup_all(self, name) -> Set[str]:
        return {file.name for file in self.directory.glob(name)}

    def remove(self, name):
        self._lookup_path(name).unlink()


class external:
    def __init__(self, name: str):
        """External objects are used as a representation for outsourced data.
        You should not create them directly.

        The external data is by default stored inside `<pytest_config_dir>/.inline-snapshot/external`,
        where `<pytest_config_dir>` is replaced by the directory containing the Pytest configuration file, if any.
        To store data in a different location, set the `storage-dir` option in pyproject.toml.
        Data which is outsourced but not referenced in the source code jet has a '-new' suffix in the filename.

        Parameters:
            name: the name of the external stored object.
        """

        m = re.fullmatch(r"([0-9a-fA-F]*)\*?(\.[a-zA-Z0-9]*)", name)

        if m:
            self._filename = name
            self._storage = "hash"
        elif ":" in name:
            self._storage, self._filename = name.split(":", 1)
        else:
            raise ValueError(
                "path has to be of the form <hash>.<suffix> or <partial_hash>*.<suffix>"
            )

    def __repr__(self):
        """Returns the representation of the external object.

        The length of the hash can be specified in the
        [config](configuration.md).
        """

        return f'external("{self._storage}:{self._filename}")'

    def __eq__(self, other):
        """Two external objects are equal if they have the same hash and
        suffix."""
        try:
            value = self._load_value()
        except HashError:
            return False

        if isinstance(other, external):
            return value == other._load_value()
        elif isinstance(other, GenericValue):
            return NotImplemented
        else:
            return value == other

    def _load_value(self):
        assert state().storage is not None
        return state().storage.read(self._filename)


# outsource(data,suffix=".json",storage="hash",path="some/local/path")


def outsource(data: Union[str, bytes], *, suffix: Optional[str] = None) -> external:
    """Outsource some data into an external file.

    ``` pycon
    >>> png_data = b"some_bytes"  # should be the replaced with your actual data
    >>> outsource(png_data, suffix=".png")
    external("212974ed1835*.png")

    ```

    Parameters:
        data: data which should be outsourced. strings are encoded with `"utf-8"`.

        suffix: overwrite file suffix. The default is `".bin"` if data is an instance of `#!python bytes` and `".txt"` for `#!python str`.

    Returns:
        The external data.
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
        if suffix is None:
            suffix = ".txt"

    elif isinstance(data, bytes):
        if suffix is None:
            suffix = ".bin"
    else:
        raise TypeError("data has to be of type bytes | str")

    if not suffix or suffix[0] != ".":
        raise ValueError("suffix has to start with a '.' like '.png'")

    m = hashlib.sha256()
    m.update(data)
    hash = m.hexdigest()

    storage = state().storage

    assert storage is not None

    name = hash + suffix

    if not storage.lookup_all(name):
        path = hash + "-new" + suffix
        storage.save(path, data)

    hash = hash[: _config.config.hash_length]
    name = hash + "*" + suffix

    e = external("hash:" + name)

    return e
