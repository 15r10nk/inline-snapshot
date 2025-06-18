## General


Storing snapshots in the source code is the main feature of inline snapshots.
This has the advantage that you can easily see changes in code reviews. But it also has some problems:

* It is problematic to snapshot a lot of data, because it takes up a lot of space in your tests.
* Binary data or images are not readable in your tests.

The `external()` solves this problem and integrates itself nicely with the inline snapshot.
It stores a reference to the external data in a special `external()` object which can be used like `snapshot()`.

There are different storage protocols like [*hash*](#hash) or [*uuid*](#uuid) and different file formats like *.txt*, *.bin*, and *.json*. It is also possible to implement custom file formats.


Example:

=== "original code"
    <!-- inline-snapshot: first_block outcome-failed=1 outcome-errors=1 -->
    ``` python
    from inline_snapshot import external


    def test_something():
        # inline-snapshot can figure out the correct file-types
        assert "string" == external()
        assert b"bytes" == external()

        # or you can specify the file type
        assert ["json", "like", "data"] == external(".json")

        # or the storage
        assert "other text" == external("uuid:")

        # or both
        assert "other text" == external("uuid:.json")
    ```

=== "--inline-snapshot=create"
    <!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
    ``` python hl_lines="6 7 10 11 12 15 16 17 20 21 22"
    from inline_snapshot import external


    def test_something():
        # inline-snapshot can figure out the correct file-types
        assert "string" == external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.txt")
        assert b"bytes" == external("uuid:f728b4fa-4248-4e3a-8a5d-2f346baa9455.bin")

        # or you can specify the file type
        assert ["json", "like", "data"] == external(
            "uuid:eb1167b3-67a9-4378-bc65-c1e582e2e662.json"
        )

        # or the storage
        assert "other text" == external(
            "uuid:f7c1bd87-4da5-4709-9471-3d60c8a70639.txt"
        )

        # or both
        assert "other text" == external(
            "uuid:e443df78-9558-467f-9ba9-1faf7a024204.json"
        )
    ```

The `external()` can be used inside other data structures.

=== "original code"
    <!-- inline-snapshot: first_block outcome-failed=1 outcome-errors=1 -->
    ``` python
    from inline_snapshot import snapshot, external


    def test_something():
        assert ["long text\n" * times for times in [1, 2, 1000]] == snapshot(
            [..., ..., external()]
        )
    ```

=== "--inline-snapshot=create,fix"
    <!-- inline-snapshot: create fix outcome-passed=1 outcome-errors=1 -->
    ``` python hl_lines="6 7 8 9 10 11 12 13"
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

### Storage protocols

#### Uuid

The `uuid:` storage protocol is the default protocol and stores the external files relative to the test files in `__inline_snapshot__/<test_file>/<qualname>/<uuid>.suffix`. The usage of an uuid allows inline-snapshot to find the external file even if filenames or the snapshot order in a test function have changed.

#### Hash

The `hash:` storage can be used to store snapshot files based on the hash of their content.

### Formats

inline-snapshot supports several build-in formats for external snapshots. The used format is determined by the given datatype bytes are stored in a `.bin` file and strings in a `.txt` file by default.

You can also store more complex data in JSON files but you have to do this explicit by using `external(".json")`.

You can also use format aliases if you want to use specific file suffixes which have a equal handling like existing formats

=== "original code"
    <!-- inline-snapshot: first_block outcome-failed=1 outcome-errors=1 -->
    ``` python
    from inline_snapshot import register_format_alias, external

    register_format_alias(".html", ".txt")


    def test():
        assert "<html></html>" == external(".html")
    ```

=== "--inline-snapshot=create"
    <!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
    ``` python hl_lines="7 8 9"
    from inline_snapshot import register_format_alias, external

    register_format_alias(".html", ".txt")


    def test():
        assert "<html></html>" == external(
            "uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.html"
        )
    ```

#### Buildin formats

inline-snapshot provides the following default formats


<!--[[[cog
from inline_snapshot._global_state import state
import cog

cog.out("|Name|Suffix|Description|\n")
cog.out("|---|---|---|\n")
for format in state().all_formats.values():
    required="(required)" if format.suffix_required else ""

    cog.out(f"|*{format.__name__}*| `{format.suffix}` {required}| {format.__doc__}|\n")

]]]-->
|Name|Suffix|Description|
|---|---|---|
|*BinaryFormat*| `.bin` | stores bytes in `.bin` files and shows them as hexdump|
|*TextFormat*| `.txt` | stores strings in `.txt` files|
|*JsonFormat*| `.json` (required)| stores the data with `json.dump()`|
<!--[[[end]]]-->



#### Custom Formats

It is also possible to define handler for your custom file formats.

=== "original code"
    <!-- inline-snapshot: first_block outcome-failed=1 outcome-errors=1 -->
    ``` python
    from dataclasses import dataclass
    from pathlib import Path
    from typing import List
    from inline_snapshot import register_format, TextDiff, Format, external


    @dataclass
    class Array:
        numbers: List[int]


    @register_format
    class ArrayFormat(TextDiff, Format[Array]):
        suffix = ".arr"

        # suffix_required = True

        @staticmethod
        def isHandled(data: object):
            return isinstance(data, Array)

        @staticmethod
        def encode(value: Array, path: Path):
            with path.open("w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(map(str, value.numbers)))

        @staticmethod
        def decode(path: Path) -> Array:
            with path.open("r", encoding="utf-8", newline="\n") as f:
                return Array(list(map(int, f.read().splitlines())))


    def test():
        assert Array([1, 2, 3]) == external()
    ```

=== "--inline-snapshot=create"
    <!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
    ``` python hl_lines="34 35 36"
    from dataclasses import dataclass
    from pathlib import Path
    from typing import List
    from inline_snapshot import register_format, TextDiff, Format, external


    @dataclass
    class Array:
        numbers: List[int]


    @register_format
    class ArrayFormat(TextDiff, Format[Array]):
        suffix = ".arr"

        # suffix_required = True

        @staticmethod
        def isHandled(data: object):
            return isinstance(data, Array)

        @staticmethod
        def encode(value: Array, path: Path):
            with path.open("w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(map(str, value.numbers)))

        @staticmethod
        def decode(path: Path) -> Array:
            with path.open("r", encoding="utf-8", newline="\n") as f:
                return Array(list(map(int, f.read().splitlines())))


    def test():
        assert Array([1, 2, 3]) == external(
            "uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.arr"
        )
    ```

`isHandled()` should return `True` for all datatypes which are handled by this format. You will have to use `external(".arr")` when the given value is handled by multiple formats.

`suffix_required` is `False` by default and can be set to `True` if you implement a generic format which should work with all sorts of datatypes (like the `JsonFormat` does) where `isHandled()` returns always `True`.
This allows you to use `assert "text" == external()` without providing an explicit `".txt"` suffix for external and requires that you use the `".json"` suffix explicit when you want to use the `JsonFormat`.


#### Report

inline-snapshot needs to know how changes in your external files should be displayed. `TextDiff` and `BinaryDiff` can be used as a mixin class (see the example in [custom formats](#custom-formats)) to provide generic representation for text or binary formats but you can also define custom  functions for your files.

* `rich_diff()` is used every time your the external snapshot value is changed and should show the difference between the original and new version in some human readable form.
* `rich_show()`: is used every time an external snapshot is created and should show an human readable form of the initial value.



=== "conftest.py"
    <!-- inline-snapshot-lib: conftest.py -->
    ``` python
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

        def isHandled(self, data: object):
            return isinstance(data, NumberSet)

        def encode(self, value: NumberSet, path: Path):
            with path.open("w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(sorted(map(str, value.numbers))))

        def decode(self, path: Path) -> NumberSet:
            with path.open("r", encoding="utf-8", newline="\n") as f:
                return NumberSet(set(map(int, f.read().splitlines())))
    ```

=== "number_set.py"
    <!-- inline-snapshot-lib: number_set.py -->
    ``` python
    from dataclasses import dataclass
    from typing import Set


    @dataclass
    class NumberSet:
        numbers: Set[int]
    ```


The custom format is then used every time an `Array` is compared with an empty external.

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


### outsource()

`outsource()` can be used to define that a value should be stored in an external object when you create the value which you want to snapshot.
This is useful in cases where you already know that a value can only be stored externally.

=== "original code"
    <!-- inline-snapshot: first_block outcome-passed=1 outcome-errors=1 -->
    ``` python
    from inline_snapshot import outsource, register_format_alias, snapshot

    register_format_alias(".png", ".bin")


    def check_captcha(input_data):
        # do something with input_data ...
        the_data = b"image data ..."

        return {
            "size": "200x100",
            "difficulty": 8,
            "picture": outsource(the_data, suffix=".png"),
        }


    def test_captcha():
        assert check_captcha("abc") == snapshot()
    ```

=== "--inline-snapshot=create"
    <!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
    ``` python hl_lines="3 4 20 21 22 23 24 25 26"
    from inline_snapshot import outsource, register_format_alias, snapshot

    from inline_snapshot import external

    register_format_alias(".png", ".bin")


    def check_captcha(input_data):
        # do something with input_data ...
        the_data = b"image data ..."

        return {
            "size": "200x100",
            "difficulty": 8,
            "picture": outsource(the_data, suffix=".png"),
        }


    def test_captcha():
        assert check_captcha("abc") == snapshot(
            {
                "size": "200x100",
                "difficulty": 8,
                "picture": external("hash:0da2cc316111*.png"),
            }
        )
    ```
!!! info
    It is not possible to specify the storage protocol because this is something which should be in the control of the user who uses this value.

    `outsource()` uses currently always the *hash* protocol when it creates new external object.
    This is a limitation which will be fixed in the future.
    It is still possible to use `#!python external("uuid:")` if you want to store it in an different store.


## pytest options

It interacts with the following `--inline-snapshot` flags:

- `create` creates new external files.
- `fix` changes external files.
- `trim` removes every snapshots form the storage which is not referenced with `external(...)` in the code.
