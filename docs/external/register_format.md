## General

`register_format()` allows you to add support for your custom file formats, such as the following `Array` type.

<!-- inline-snapshot-lib: my_array.py -->
``` python title="my_array.py"
from dataclasses import dataclass
from typing import List


@dataclass
class Array:
    numbers: List[int]
```
[](){#array-example}
<!-- inline-snapshot-lib: conftest.py -->
``` python title="conftest.py"
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

<!-- inline-snapshot: first_block outcome-failed=1 outcome-errors=1 -->
``` python
from my_array import Array
from inline_snapshot import external


def test_array():
    assert Array([1, 2, 3]) == external()
```

inline-snapshot will check if the type matches by using `is_format_for()` and create a file with the given suffix.

<!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
``` python hl_lines="6 7 8"
from my_array import Array
from inline_snapshot import external


def test_array():
    assert Array([1, 2, 3]) == external(
        "uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.arr"
    )
```


### Report

inline-snapshot needs to know how changes in your external files should be displayed. `TextDiff` and `BinaryDiff` can be used as mixin classes (see the `Array` example (above)[#array-example]) to provide generic representations for text or binary formats, but you can also define custom functions for your files.

* `rich_diff()` is used every time the external snapshot value is changed and should show the difference between the original and new versions in a human-readable form.
* `rich_show()` is used every time an external snapshot is created and should show a human-readable form of the initial value.

<!-- inline-snapshot-lib-set: conftest.py -->
``` python title="conftest.py"
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

<!-- inline-snapshot-lib: number_set.py -->
``` python title="number_set.py"
from dataclasses import dataclass
from typing import Set


@dataclass
class NumberSet:
    numbers: Set[int]
```

The custom format is then used every time a `NumberSet` is compared with an empty external.

=== "example pytest output"

    ![](/assets/number_set_output.png)

=== "example"
    <!-- inline-snapshot: create first_block outcome-failed=1 -->
    ``` python
    from inline_snapshot import external
    from number_set import NumberSet


    def test():
        assert NumberSet([1, 2, 5]) == external("hash:b85198032326*.numberset")
        assert NumberSet([1, 2, 8]) == external("hash:f8a68eb0c510*.numberset")
    ```

## Reference

::: inline_snapshot
    options:
      heading_level: 3
      members: [register_format, register_format_alias, Format]
      show_root_heading: false
      show_bases: false
      show_source: false
