## General

Info

This feature is currently under development. See this [issue](https://github.com/15r10nk/inline-snapshot/issues/86) for more information.

Storing snapshots in the source code is the main feature of inline snapshots. This has the advantage that you can easily see changes in code reviews. But it also has some problems:

- It is problematic to snapshot a lot of data, because it takes up a lot of space in your tests.
- Binary data or images are not readable in your tests.

The `outsource()` function solves this problem and integrates itself nicely with the inline snapshot. It stores the data in a special `external()` object that can be compared in snapshots. The object is represented by the hash of the data. The actual data is stored in a separate file in your project.

This allows the test to be renamed and moved around in your code without losing the connection to the stored data.

Example:

```
from inline_snapshot import snapshot, outsource


def test_something():
    assert outsource("long text\n" * 1000) == snapshot()

```

```
from inline_snapshot import snapshot, outsource

from inline_snapshot import external


def test_something():
    assert outsource("long text\n" * 1000) == snapshot(
        external("f5a956460453*.txt")
    )

```

The `external` object can be used inside other data structures.

```
from inline_snapshot import snapshot, outsource


def test_something():
    assert [
        outsource("long text\n" * times) for times in [50, 100, 1000]
    ] == snapshot()

```

```
from inline_snapshot import snapshot, outsource

from inline_snapshot import external


def test_something():
    assert [
        outsource("long text\n" * times) for times in [50, 100, 1000]
    ] == snapshot(
        [
            external("362ad8374ed6*.txt"),
            external("5755afea3f8d*.txt"),
            external("f5a956460453*.txt"),
        ]
    )

```

## API

## `inline_snapshot.outsource(data, *, suffix=None)`

Outsource some data into an external file.

```
>>> png_data = b"some_bytes"  # should be the replaced with your actual data
>>> outsource(png_data, suffix=".png")
external("212974ed1835*.png")

```

Parameters:

| Name     | Type                | Description                                                                                      | Default    |
| -------- | ------------------- | ------------------------------------------------------------------------------------------------ | ---------- |
| `data`   | `Union[str, bytes]` | data which should be outsourced. strings are encoded with "utf-8".                               | *required* |
| `suffix` | `Optional[str]`     | overwrite file suffix. The default is ".bin" if data is an instance of bytes and ".txt" for str. | `None`     |

Returns:

| Type       | Description        |
| ---------- | ------------------ |
| `external` | The external data. |

Source code in `src/inline_snapshot/_external.py`

````
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

    return external(name)

````

## `inline_snapshot.external`

Source code in `src/inline_snapshot/_external.py`

```
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
            self._hash, self._suffix = m.groups()
        else:
            raise ValueError(
                "path has to be of the form <hash>.<suffix> or <partial_hash>*.<suffix>"
            )

    @property
    def _path(self):
        return f"{self._hash}*{self._suffix}"

    def __repr__(self):
        """Returns the representation of the external object.

        The length of the hash can be specified in the
        [config](configuration.md).
        """
        hash = self._hash[: _config.config.hash_length]

        if len(hash) == 64:
            return f'external("{hash}{self._suffix}")'
        else:
            return f'external("{hash}*{self._suffix}")'

    def __eq__(self, other):
        """Two external objects are equal if they have the same hash and
        suffix."""
        if not isinstance(other, external):
            return NotImplemented

        min_hash_len = min(len(self._hash), len(other._hash))

        if self._hash[:min_hash_len] != other._hash[:min_hash_len]:
            return False

        if self._suffix != other._suffix:
            return False

        return True

    def _load_value(self):
        assert state().storage is not None
        return state().storage.read(self._path)

```

### `__eq__(other)`

Two external objects are equal if they have the same hash and suffix.

Source code in `src/inline_snapshot/_external.py`

```
def __eq__(self, other):
    """Two external objects are equal if they have the same hash and
    suffix."""
    if not isinstance(other, external):
        return NotImplemented

    min_hash_len = min(len(self._hash), len(other._hash))

    if self._hash[:min_hash_len] != other._hash[:min_hash_len]:
        return False

    if self._suffix != other._suffix:
        return False

    return True

```

### `__init__(name)`

External objects are used as a representation for outsourced data. You should not create them directly.

The external data is by default stored inside `<pytest_config_dir>/.inline-snapshot/external`, where `<pytest_config_dir>` is replaced by the directory containing the Pytest configuration file, if any. To store data in a different location, set the `storage-dir` option in pyproject.toml. Data which is outsourced but not referenced in the source code jet has a '-new' suffix in the filename.

Parameters:

| Name   | Type  | Description                             | Default    |
| ------ | ----- | --------------------------------------- | ---------- |
| `name` | `str` | the name of the external stored object. | *required* |

Source code in `src/inline_snapshot/_external.py`

```
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
        self._hash, self._suffix = m.groups()
    else:
        raise ValueError(
            "path has to be of the form <hash>.<suffix> or <partial_hash>*.<suffix>"
        )

```

### `__repr__()`

Returns the representation of the external object.

The length of the hash can be specified in the [config](../configuration/).

Source code in `src/inline_snapshot/_external.py`

```
def __repr__(self):
    """Returns the representation of the external object.

    The length of the hash can be specified in the
    [config](configuration.md).
    """
    hash = self._hash[: _config.config.hash_length]

    if len(hash) == 64:
        return f'external("{hash}{self._suffix}")'
    else:
        return f'external("{hash}*{self._suffix}")'

```

## pytest options

It interacts with the following `--inline-snapshot` flags:

- `trim` removes every snapshots form the storage which is not referenced with `external(...)` in the code.
