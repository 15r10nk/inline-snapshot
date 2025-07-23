`outsource()` can be used to declare that a value should be stored in an external object when you create it.
This is useful in cases where you already know that a value can only be stored externally, and you want to return it from a function, for example.

<!-- inline-snapshot: first_block outcome-passed=1 outcome-errors=1 -->
``` python
from inline_snapshot import outsource, register_format_alias, snapshot

register_format_alias(".png", ".bin")


def check_captcha(input_data):
    # Perform operations on input_data ...
    the_data = b"image data ..."

    return {
        "size": "200x100",
        "difficulty": 8,
        "picture": outsource(the_data, suffix=".png"),
    }


def test_captcha():
    assert check_captcha("abc") == snapshot()
```

inline-snapshot always generates an external object in this case.

<!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
``` python hl_lines="3 4 20 21 22 23 24 25 26"
from inline_snapshot import outsource, register_format_alias, snapshot

from inline_snapshot import external

register_format_alias(".png", ".bin")


def check_captcha(input_data):
    # Perform operations on input_data ...
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

`outsource()` was the only way to create external objects until inline-snapshot 0.24. External objects can now also be created with `external()` and used like `snapshot()`.

!!! info
    It is not possible to specify the storage protocol when you call `outsource()` because this is something that should be under the control of the user who uses this external object.

!!! limitation
    `outsource()` currently always uses the *hash* protocol when it creates a new external object.
    This is a limitation that will be addressed in the future.
    It is possible to change it later to `#!python external("uuid:")` manually if you want to store it in a different location.
