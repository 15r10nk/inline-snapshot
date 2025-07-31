## General

`register_format()` allows you to add support for your custom file formats, such as the following `Array` type.

my_array.py

```
from dataclasses import dataclass
from typing import List


@dataclass
class Array:
    numbers: List[int]

```

conftest.py

```
from pathlib import Path
from inline_snapshot import register_format, TextDiff, Format

from my_array import Array


@register_format
class ArrayFormat(TextDiff, Format[Array]):
    suffix = ".arr"

    @staticmethod
    def is_format_for(data: object):
        return isinstance(data, Array)

    @staticmethod
    def encode(value: Array, path: Path):
        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(map(str, value.numbers)))

    @staticmethod
    def decode(path: Path) -> Array:
        with path.open("r", encoding="utf-8", newline="\n") as f:
            return Array(list(map(int, f.read().splitlines())))

```

You can then use `external()` to save this type into an external file.

```
from my_array import Array
from inline_snapshot import external


def test_array():
    assert Array([1, 2, 3]) == external()

```

inline-snapshot will check if the type matches by using `is_format_for()` and create a file with the given suffix.

```
from my_array import Array
from inline_snapshot import external


def test_array():
    assert Array([1, 2, 3]) == external(
        "uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.arr"
    )

```

### Report

inline-snapshot needs to know how changes in your external files should be displayed. `TextDiff` and `BinaryDiff` can be used as mixin classes (see the `Array` example (above)[#array-example]) to provide generic representations for text or binary formats, but you can also define custom functions for your files.

- `rich_diff()` is used every time the external snapshot value is changed and should show the difference between the original and new versions in a human-readable form.
- `rich_show()` is used every time an external snapshot is created and should show a human-readable form of the initial value.

conftest.py

```
from pathlib import Path
from inline_snapshot import register_format, Format, external
from number_set import NumberSet


@register_format
class NumberSetFormat(Format[NumberSet]):
    suffix = ".numberset"

    def rich_diff(self, original: Path, new: Path):
        original_numbers = set(self.decode(original).numbers)
        new_numbers = set(self.decode(new).numbers)

        return (
            f"new numbers: [green]{new_numbers-original_numbers}[/]\n"
            f"removed numbers: [red]{original_numbers-new_numbers}[/]"
        )

    def rich_show(self, path: Path):
        return " ".join(f"[blue]{n}[/]" for n in self.decode(path).numbers)

    def is_format_for(self, data: object):
        return isinstance(data, NumberSet)

    def encode(self, value: NumberSet, path: Path):
        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(sorted(map(str, value.numbers))))

    def decode(self, path: Path) -> NumberSet:
        with path.open("r", encoding="utf-8", newline="\n") as f:
            return NumberSet(set(map(int, f.read().splitlines())))

```

number_set.py

```
from dataclasses import dataclass
from typing import Set


@dataclass
class NumberSet:
    numbers: Set[int]

```

The custom format is then used every time a `NumberSet` is compared with an empty external.

```
from inline_snapshot import external
from number_set import NumberSet


def test():
    assert NumberSet([1, 2, 5]) == external("hash:b85198032326*.numberset")
    assert NumberSet([1, 2, 8]) == external("hash:f8a68eb0c510*.numberset")

```

## Reference

### `Format`

Base class for the Format Protocol.

#### `priority = 0`

Determines the correct format when multiple format handlers can handle a given value (`is_format_for`).

*priority* is `0` by default and can be set to a smaller number for generic formats that work with many data types (e.g., *.json*), where `is_format_for()` also returns `True` for `str` and `bytes`. This allows you to use `assert "text" == external()` without explicitly providing a `".txt"` suffix to distinguish it from `".json"`.

A higher *priority* can be used for more specific formats, such as bytes with a `b"\x89PNG"` prefix that should be stored as *.png* files.

#### `suffix`

The suffix associated with this format handler.

Every format implementation must define a suffix. This suffix is used when the external file is written and is required to find the correct format handler when the file is read again.

#### `decode(path)`

Reads the value from the specified path.

Parameters:

| Name   | Type   | Description                                             | Default    |
| ------ | ------ | ------------------------------------------------------- | ---------- |
| `path` | `Path` | The path to a temporary file where the value is stored. | *required* |

Returns:

| Type | Description                       |
| ---- | --------------------------------- |
| `T`  | The value of the external object. |

#### `encode(value, path)`

Converts the value and stores it in the specified path.

Parameters:

| Name    | Type   | Description                                                    | Default    |
| ------- | ------ | -------------------------------------------------------------- | ---------- |
| `value` | `T`    | The value to be stored.                                        | *required* |
| `path`  | `Path` | The path to a temporary file where the value should be stored. | *required* |

#### `is_format_for(value)`

Determines if this format handler can handle the given value.

This function is used to find the correct format handler when no suffix is provided.

```
assert value == external()

```

Parameters:

| Name    | Type     | Description                | Default    |
| ------- | -------- | -------------------------- | ---------- |
| `value` | `object` | The value to be formatted. | *required* |

Returns:

| Type   | Description                                                 |
| ------ | ----------------------------------------------------------- |
| `bool` | True if the value is handled by this format implementation. |

#### `rich_diff(original, new)`

Displays a diff between the original and new files.

Parameters:

| Name       | Type   | Description                             | Default    |
| ---------- | ------ | --------------------------------------- | ---------- |
| `original` | `Path` | The path to the original external file. | *required* |
| `new`      | `Path` | The path to the new external file.      | *required* |

Returns:

| Type             | Description                                                   |
| ---------------- | ------------------------------------------------------------- |
| `RenderableType` | A rich renderable object representing the diff. This can be a |
| `RenderableType` | textual diff or another type of representation.               |

#### `rich_show(path)`

Displays a representation of a newly created external object.

Parameters:

| Name   | Type   | Description                    | Default    |
| ------ | ------ | ------------------------------ | ---------- |
| `path` | `Path` | The path to the external file. | *required* |

Returns:

| Type             | Description                                               |
| ---------------- | --------------------------------------------------------- |
| `RenderableType` | A rich renderable object representing the new object. The |
| `RenderableType` | representation should be concise.                         |

### `register_format(format=None, *, replace_handler=False)`

Registers a new format handler for the suffix `format.suffix`.

This function can also be used as a decorator:

```
@register_format
class MyFormat: ...

```

which is equivalent to:

```
register_format(MyFormat())

```

Parameters:

| Name              | Type                      | Description                                                | Default |
| ----------------- | ------------------------- | ---------------------------------------------------------- | ------- |
| `format`          | \`type\[Format[FormatT]\] | Format[FormatT]                                            | None\`  |
| `replace_handler` | `bool`                    | If True, replaces an existing handler for the same suffix. | `False` |

Raises:

| Type         | Description                                                                             |
| ------------ | --------------------------------------------------------------------------------------- |
| `UsageError` | If a handler for the same suffix already exists and replace_handler is not set to True. |

### `register_format_alias(suffix, format)`

Registers an alias for a given format suffix.

Parameters:

| Name     | Type  | Description                                           | Default    |
| -------- | ----- | ----------------------------------------------------- | ---------- |
| `suffix` | `str` | The suffix to register the alias for.                 | *required* |
| `format` | `str` | The suffix of the format that should be used instead. | *required* |

Notes

The alias suffix is used to find the correct format handler.
