`@customize` allows you to register special hooks to control how inline-snapshot generates your snapshots.
You should use it when you find yourself manually editing snapshots after they were created by inline-snapshot.

`@customize` hooks can have the following arguments (but you do not have to use all of them).

* **value:** the value of your snapshot that is currently being converted to source code.
* **builder:** your `Builder` object can be used to create Custom objects that represent your new code.
* **local_vars:** a list of objects with `name` and `value` attributes that represent the local variables that are usable in your snapshot.
* **global_vars:** same as for `local_vars`, but for global variables.

## Custom constructor methods
One use case might be that you have a dataclass with a special constructor function that can be used for specific instances of this dataclass, and you want inline-snapshot to use this constructor when possible.

<!-- inline-snapshot-lib-set: rect.py -->
``` python
from dataclasses import dataclass


@dataclass
class Rect:
    width: int
    height: int

    @staticmethod
    def make_quadrat(size):
        return Rect(size, size)
```

You can define a hook in your `conftest.py` that checks if your value is a square and calls the correct constructor function.
Inline-snapshot tries each hook until it finds one that does not return None.
It keeps converting this value until a hook returns a Custom object, which can be created with the `create_*` methods of the [`Builder`][inline_snapshot.Builder].

<!-- inline-snapshot-lib-set: conftest.py -->
``` python
from rect import Rect
from inline_snapshot import customize
from inline_snapshot import Builder


@customize
def quadrat_handler(value, builder: Builder):
    if isinstance(value, Rect) and value.width == value.height:
        return builder.create_call(Rect.make_quadrat, [value.width])
```

This allows you to influence the code that is created by inline-snapshot.

<!-- inline-snapshot: create fix first_block outcome-passed=1 -->
``` python
from inline_snapshot import snapshot
from rect import Rect


def test_quadrat():
    assert Rect.make_quadrat(5) == snapshot(Rect.make_quadrat(5))  # (1)!
    assert Rect(1, 1) == snapshot(Rect.make_quadrat(1))  # (2)!
    assert Rect(1, 2) == snapshot(Rect(width=1, height=2))  # (3)!
```

1. Your handler is used because you created a square
2. Your handler is used because you created a rect that happens to have the same width and height
3. Your handler is not used because width and height are different

## dirty-equal expressions
It can also be used to instruct inline-snapshot to use specific dirty-equals expressions for specific values.

<!-- inline-snapshot-lib-set: conftest.py -->
``` python
from inline_snapshot import customize
from inline_snapshot import Builder
from dirty_equals import IsNow


@customize
def is_now_handler(value):
    if value == IsNow():
        return IsNow
```

Inline-snapshot provides a handler that can convert dirty-equals expressions back into source code. This allows you to return `IsNow` here without the need to construct a custom object with the builder.
This works because the value is converted with the customize functions until one hook uses the builder to create a Custom object.

<!-- inline-snapshot: create fix first_block outcome-passed=1 -->
``` python
from inline_snapshot import snapshot
from datetime import datetime

from dirty_equals import IsNow  # (1)!


def test_is_now():
    assert datetime.now() == snapshot(IsNow)
```

1. Inline-snapshot also creates the imports when they are missing

!!! important
    Inline-snapshot will never change the dirty-equals expressions in your code because they are unmanaged.
    Using `@customize` with dirty-equals is a one-way ticket. Once the code is created, inline-snapshot does not know if it was created by inline-snapshot itself or by the user and will not change it, because it has to assume that it was created by the user.


## Conditional external objects

`create_external` can be used to store values in external files if a specific criterion is met.

<!-- inline-snapshot-lib-set: conftest.py -->
``` python
from inline_snapshot import customize
from inline_snapshot import Builder
from dirty_equals import IsNow


@customize
def is_now_handler(value, builder: Builder):
    if isinstance(value, str) and value.count("\n") > 5:
        return builder.create_external(value)
```

<!-- inline-snapshot: create fix first_block outcome-passed=1 outcome-errors=1 -->
``` python
from inline_snapshot import snapshot
from datetime import datetime

from inline_snapshot import external


def test_long_strings():
    assert "a\nb\nc" == snapshot(
        """\
a
b
c\
"""
    )
    assert "a\n" * 50 == snapshot(
        external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.txt")
    )
```

## Reusing local variables

There are times when your local or global variables become part of your snapshots, like uuids or user names.
Customize hooks accept `local_vars` and `global_vars` as arguments that can be used to generate the code.

<!-- inline-snapshot-lib-set: conftest.py -->
``` python title="conftest.py"
from inline_snapshot import customize
from inline_snapshot import Builder


@customize
def local_var_handler(value, local_vars):
    for local in local_vars:
        if local.name.startswith("v_") and local.value == value:
            return local
```

We check all local variables to see if they match our naming convention and are equal to the value that is part of our snapshot, and return the local if we find one that fits the criteria.


<!-- inline-snapshot: create fix first_block outcome-passed=1 -->
``` python title="test_user.py"
from inline_snapshot import snapshot
from datetime import datetime

from inline_snapshot import external


def get_data(user):
    return {"user": user, "age": 55}


def test_user():
    v_user = "Bob"
    some_number = 50 + 5

    assert get_data(v_user) == snapshot({"user": v_user, "age": 55})
```

Inline-snapshot uses `v_user` because it met the criteria in your customization hook, but not `some_number` because it does not start with `v_`.
You can also do this only for specific types of objects or for a whitelist of variable names.
It is up to you to set the rules that work best in your project.

!!! note
    It is not recommended to check only for the value because this might result in local variables which become part of the snapshot just because they are equal to the value and not because they should be there (see `age=55` in the example above).
    This is also the reason why inline-snapshot does not provide default customizations that check your local variables.
    The rules are project specific and what might work well for one project can cause problems for others.

# Reference

::: inline_snapshot
    options:
      heading_level: 3
      members: [customize,Builder,Custom]
      show_root_heading: false
      show_bases: false
      show_source: false
