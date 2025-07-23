Storing snapshots in the source code is the main feature of inline snapshots. This has the advantage that you can easily see changes in code reviews. However, it also has some drawbacks:

- It is problematic to snapshot a large amount of data, as it consumes significant space in your tests.
- Binary data or images are not human-readable in your tests.

`external()` solves this problem and integrates nicely with inline snapshots. It stores a reference to the external data in a special `external()` object, which can be used like `snapshot()`.

There are different storage protocols, such as [*hash*](#hash) or [*uuid*](#uuid), and different file formats, such as *.txt*, *.bin*, and *.json*. It is also possible to implement [*custom*](../register_format/) file formats.

Example:

```
from inline_snapshot import external


def test_something():
    # inline-snapshot can determine the correct file types
    assert "string" == external()
    assert b"bytes" == external()

    # Data structures with lists and dictionaries are stored as JSON
    assert ["json", "like", "data"] == external()

    # You can also explicitly specify the storage protocol
    assert "other text" == external("uuid:")

    # And the format (.json instead of the default .txt in this case)
    assert "other text" == external("uuid:.json")

```

inline-snapshot will then fill in the missing parts when you create your snapshots. It will keep your specified protocols and file types and generate names for your snapshots.

```
from inline_snapshot import external


def test_something():
    # inline-snapshot can determine the correct file types
    assert "string" == external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.txt")
    assert b"bytes" == external("uuid:f728b4fa-4248-4e3a-8a5d-2f346baa9455.bin")

    # Data structures with lists and dictionaries are stored as JSON
    assert ["json", "like", "data"] == external(
        "uuid:eb1167b3-67a9-4378-bc65-c1e582e2e662.json"
    )

    # You can also explicitly specify the storage protocol
    assert "other text" == external(
        "uuid:f7c1bd87-4da5-4709-9471-3d60c8a70639.txt"
    )

    # And the format (.json instead of the default .txt in this case)
    assert "other text" == external(
        "uuid:e443df78-9558-467f-9ba9-1faf7a024204.json"
    )

```

The `external()` function can also be used inside other data structures.

```
from inline_snapshot import snapshot, external


def test_something():
    assert ["long text\n" * times for times in [1, 2, 1000]] == snapshot(
        [..., ..., external()]
    )

```

```
from inline_snapshot import snapshot, external


def test_something():
    assert ["long text\n" * times for times in [1, 2, 1000]] == snapshot(
        [
            "long text\n",
            """\
long text
long text
""",
            external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.txt"),
        ]
    )

```

## Storage Protocols

### UUID

The `uuid:` storage protocol is the default protocol and stores the external files relative to the test files in `__inline_snapshot__/<test_file>/<qualname>/<uuid>.suffix`.

- Files are co-located with the file/function where your value is used.
- The use of a UUID allows inline-snapshot to find the external file even if file or function names of a test function have changed.
- Distinguishing multiple external snapshots in the same function remains challenging.

### Hash

The `hash:` storage can be used to store snapshot files based on the hash of their content. This was the first storage protocol supported by inline-snapshot and can still be useful in some cases. It also preserves backward compatibility with older inline-snapshot versions.

The external data is by default stored inside `<pytest_config_dir>/.inline-snapshot/external`, where `<pytest_config_dir>` is replaced by the directory containing the Pytest configuration file, if any. To store data in a different location, set the `storage-dir` option in pyproject.toml.

- Value changes cause source code changes because the hash changes.
- GitHub/GitLab web UIs cannot be used to view the diffs, because the filename changes.

## Formats

inline-snapshot supports several built-in formats for external snapshots. The format used is determined by the given data type: bytes are stored in a `.bin` file, and strings are stored in a `.txt` file by default. More complex data types are stored in a `.json` file.

| Suffix  | Priority | Description                                               |
| ------- | -------- | --------------------------------------------------------- |
| `.bin`  | 0        | Stores bytes in `.bin` files and shows them as a hexdump. |
| `.txt`  | 0        | Stores strings in `.txt` files.                           |
| `.json` | -10      | Stores the data with `json.dump()`.                       |

[Custom formats](../register_format/) are also supported.

You can also use format aliases if you want to use specific file suffixes that have the same handling as existing formats. You must specify the suffix in this case.

```
from inline_snapshot import register_format_alias, external

register_format_alias(".html", ".txt")


def test():
    assert "<html></html>" == external(".html")

```

inline-snapshot uses the given suffix to create an external snapshot.

```
from inline_snapshot import register_format_alias, external

register_format_alias(".html", ".txt")


def test():
    assert "<html></html>" == external(
        "uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.html"
    )

```

Breaking Change

`register_format_alias()` is required if you used `outsource(value, suffix="html")` and are migrating from inline-snapshot prior to version 0.24.

## pytest Options

It interacts with the following `--inline-snapshot` flags:

- `create`: Creates new external files.
- `fix`: Changes external files.
- `trim`: Removes all snapshots from the storage that are not referenced with `external(...)` in the code.
