

inline-snapshot provides a plugin architecture based on [pluggy](https://pluggy.readthedocs.io/en/latest/index.html) which can be used to extend and customize it.

## Overview

Plugins allow you to customize how inline-snapshot generates code for your snapshots. The primary use case is implementing custom representation logic through the `@customize` hook, which controls how Python objects are converted into source code.

### When to Use Plugins

You should consider creating a plugin when:

- You find yourself manually editing snapshots after they are generated
- You want to use custom constructors or factory methods in your snapshots
- You need to reference local/global variables instead of hardcoding values
- You want to store certain values in external files based on specific criteria
- You need special code representations for your custom types

### Plugin Capabilities

Plugins can:

- **Customize code generation**: Control how objects appear in snapshot code (e.g., use `Color.RED` instead of `Color(255, 0, 0)`)
- **Reference variables**: Use existing local or global variables in snapshots instead of literals
- **External storage**: Automatically store large or sensitive values in external files
- **Import management**: Automatically add necessary import statements to test files

## Plugin Discovery

inline-snapshot loads the plugins at the beginning of the session.
It searches for plugins in:
* installed packages with an `inline-snapshot` entry point
* your pytest `conftest.py` files

### Loading Plugins from conftest.py

Loading plugins from the `conftest.py` files is the recommended way when you want to change the behavior of inline-snapshot in your own project.

Simply use `@customize` on functions directly in your `conftest.py`:

``` python
from inline_snapshot.plugin import customize


@customize
def my_handler(value, builder):
    # your logic
    pass
```

All customizations defined in your `conftest.py` are active globally for all your tests.

### Creating a Plugin Package

To distribute inline-snapshot plugins as a package, register your plugin class using the `inline-snapshot` entry point in your `setup.py` or `pyproject.toml`:

=== "pyproject.toml (recommended)"
    ``` toml
    [project.entry-points.inline_snapshot]
    my_plugin = "my_package.plugin:MyInlineSnapshotPlugin"
    ```

=== "setup.py"
    ``` python
    setup(
        name="my-inline-snapshot-plugin",
        entry_points={
            "inline_snapshot": [
                "my_plugin = my_package.plugin",
            ],
        },
    )
    ```

Your plugin class should contain methods decorated with `@customize`, just like in conftest.py:

``` python title="my_package/plugin.py"
from inline_snapshot.plugin import customize, Builder


@customize
def my_custom_handler(value, builder: Builder):
    # Your customization logic here
    if isinstance(value, YourCustomType):
        return builder.create_call(YourCustomType, [value.arg])
```

Once installed, the plugin will be automatically loaded by inline-snapshot.

### Plugin Specification

::: inline_snapshot.plugin
    options:
      heading_level: 3
      members: [InlineSnapshotPluginSpec]
      show_root_heading: false
      show_bases: false
      show_source: false



## Customize Examples

The following examples demonstrate common use cases for the `@customize` hook. Each example shows how to implement custom representation logic for different scenarios.

The [customize][inline_snapshot.plugin.InlineSnapshotPluginSpec.customize] hook controls how inline-snapshot generates your snapshots.
You should use it when you find yourself manually editing snapshots after they were created by inline-snapshot.


### Custom constructor methods
One use case might be that you have a dataclass with a special constructor function that can be used for specific instances of this dataclass, and you want inline-snapshot to use this constructor when possible.

<!-- inline-snapshot-lib-set: rect.py -->
``` python title="rect.py"
from dataclasses import dataclass


@dataclass
class Rect:
    width: int
    height: int

    @staticmethod
    def make_square(size):
        return Rect(size, size)
```

You can define a hook in your `conftest.py` that checks if your value is a square and calls the correct constructor function.

<!-- inline-snapshot-lib-set: conftest.py -->
``` python title="conftest.py"
from rect import Rect
from inline_snapshot.plugin import customize
from inline_snapshot.plugin import Builder


@customize
def square_handler(value, builder: Builder):
    if isinstance(value, Rect) and value.width == value.height:
        return builder.create_call(Rect.make_square, [value.width])
```

This allows you to influence the code that is created by inline-snapshot.

<!-- inline-snapshot: create fix first_block outcome-passed=1 -->
``` python title="test_square.py"
from rect import Rect
from inline_snapshot import snapshot


def test_square():
    assert Rect.make_square(5) == snapshot(Rect.make_square(5))  # (1)!
    assert Rect(1, 1) == snapshot(Rect.make_square(1))  # (2)!
    assert Rect(1, 2) == snapshot(Rect(width=1, height=2))  # (3)!
    assert [Rect(3, 3), Rect(4, 5)] == snapshot(
        [Rect.make_square(3), Rect(width=4, height=5)]
    )  # (4)!
```

1. Your handler is used because you created a square
2. Your handler is used because you created a Rect that happens to have the same width and height
3. Your handler is not used because width and height are different
4. The handler is applied recursively to each Rect inside the list - the first is converted to `make_square()` while the second uses the regular constructor

### dirty-equal expressions
It can also be used to instruct inline-snapshot to use specific dirty-equals expressions for specific values.

<!-- inline-snapshot-lib-set: conftest.py -->
``` python title="conftest.py"
from inline_snapshot.plugin import customize
from inline_snapshot.plugin import Builder
from dirty_equals import IsNow


@customize
def is_now_handler(value):
    if value == IsNow():
        return IsNow
```

As explained in the [customize hook specification][inline_snapshot.plugin.InlineSnapshotPluginSpec.customize], you can return types other than Custom objects. Inline-snapshot includes a built-in handler in its default plugin that converts dirty-equals expressions back into source code, which is why you can return `IsNow` directly without using the builder. This approach is much simpler than using `builder.create_call()` for complex dirty-equals expressions.

<!-- inline-snapshot: create fix first_block outcome-passed=1 -->
``` python title="test_is_now.py"
from datetime import datetime
from dirty_equals import IsNow  # (1)!
from inline_snapshot import snapshot


def test_is_now():
    assert datetime.now() == snapshot(IsNow)
```

1. Inline-snapshot also creates the imports when they are missing

!!! important
    Inline-snapshot will never change the dirty-equals expressions in your code because they are [unmanaged](eq_snapshot.md#unmanaged-snapshot-values).
    Using `@customize` with dirty-equals is a one-way ticket. Once the code is created, inline-snapshot does not know if it was created by inline-snapshot itself or by the user and will not change it when you change the `@customize` implementation, because it has to assume that it was created by the user.


### Conditional external objects

`create_external` can be used to store values in external files if a specific criterion is met.

<!-- inline-snapshot-lib-set: conftest.py -->
``` python title="conftest.py"
from inline_snapshot.plugin import customize
from inline_snapshot.plugin import Builder


@customize
def long_string_handler(value, builder: Builder):
    if isinstance(value, str) and value.count("\n") > 5:
        return builder.create_external(value)
```

<!-- inline-snapshot: create fix first_block outcome-passed=1 outcome-errors=1 -->
``` python title="test_long_strings.py"
from inline_snapshot import external, snapshot


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

### Reusing local variables

There are times when your local or global variables become part of your snapshots, like uuids or user names.
Customize hooks accept `local_vars` and `global_vars` as arguments that can be used to generate the code.

<!-- inline-snapshot-lib-set: conftest.py -->
``` python title="conftest.py"
from inline_snapshot.plugin import customize
from inline_snapshot.plugin import Builder


@customize
def local_var_handler(value, builder, local_vars):
    for var_name, var_value in local_vars.items():
        if var_name.startswith("v_") and var_value == value:
            return builder.create_code(var_name)
```

We check all local variables to see if they match our naming convention and are equal to the value that is part of our snapshot, and return the local variable if we find one that fits the criteria.


<!-- inline-snapshot: create fix first_block outcome-passed=1 -->
``` python title="test_user.py"
from inline_snapshot import snapshot


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
    The rules are project-specific and what might work well for one project can cause problems for others.

### Creating special code

Let's say that you have an array of secrets which are used in your code.

<!-- inline-snapshot-lib: my_secrets.py -->
``` python title="my_secrets.py"
secrets = ["some_secret", "some_other_secret"]
```

<!-- inline-snapshot-lib: get_data.py -->
``` python title="get_data.py"
from my_secrets import secrets


def get_data():
    return {"data": "large data block", "used_secret": secrets[1]}
```

The problem is that `--inline-snapshot=create` puts your secret into your test.

<!-- inline-snapshot: create first_block outcome-passed=1 -->
``` python
from get_data import get_data
from inline_snapshot import snapshot


def test_my_class():
    assert get_data() == snapshot(
        {"data": "large data block", "used_secret": "some_other_secret"}
    )
```

Maybe this is not what you want because the secret is a different one in CI or for every test run or the raw value leads to unreadable tests.
What you can do now, instead of replacing `"some_other_secret"` with `secrets[1]` by hand, is to tell inline-snapshot in your *conftest.py* how it should generate this code.

<!-- inline-snapshot-lib-set: conftest.py -->
``` python title="conftest.py"
from my_secrets import secrets
from inline_snapshot.plugin import customize, Builder, ImportFrom


@customize
def secret_handler(value, builder: Builder):
    for i, secret in enumerate(secrets):
        if value == secret:
            return builder.create_code(
                f"secrets[{i}]",
                imports=[ImportFrom("my_secrets", "secrets")],
            )
```

The [`create_code()`][inline_snapshot.plugin.Builder.create_code] method takes the desired code representation. The `imports` parameter adds the necessary import statements.

Inline-snapshot will now create the correct code and import statement when you run your tests with `--inline-snapshot=update`.

<!-- inline-snapshot: update outcome-passed=1 -->
``` python hl_lines="4 5 9"
from get_data import get_data
from inline_snapshot import snapshot

from my_secrets import secrets


def test_my_class():
    assert get_data() == snapshot(
        {"data": "large data block", "used_secret": secrets[1]}
    )
```

!!! question "why update?"
    `"some_other_secret"` was already a correct value for your assertion and `--inline-snapshot=fix` only changes code when the current value is not correct and needs to be fixed. `update` is the category for all other changes where inline-snapshot wants to generate different code which represents the same value as the code before.

    You only have to use `update` when you changed your customizations and want to use the new code representations in your existing tests. The new representation is also used by `create` or `fix` when you write new tests.

    The `update` category is not enabled by default for `--inline-snapshot=review/report`.
    You can read [here](categories.md#update) more about it.









## Reference
::: inline_snapshot.plugin
    options:
      heading_level: 3
      members: [hookimpl,customize,Builder,Custom,Import,ImportFrom]
      show_root_heading: false
      show_bases: false
      show_source: false
