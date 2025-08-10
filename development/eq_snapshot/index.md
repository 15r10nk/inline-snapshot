## General

A snapshot can be compared with any value using `==`. The value can be recorded with `--inline-snapshot=create` if the snapshot is empty. The value can later be changed with `--inline-snapshot=fix` if the value the snapshot is compared with has changed.

Example:

```
from inline_snapshot import snapshot


def test_something():
    assert 2 + 4 == snapshot()
```

```
from inline_snapshot import snapshot


def test_something():
    assert 2 + 4 == snapshot(6)
```

```
from inline_snapshot import snapshot


def test_something():
    assert 2 + 40 == snapshot(4)
```

```
from inline_snapshot import snapshot


def test_something():
    assert 2 + 40 == snapshot(42)
```

## unmanaged snapshot values

inline-snapshots manages everything inside `snapshot(...)`, which means that the developer should not change these parts, but there are cases where it is useful to give the developer the control over the snapshot content back.

Therefor some types will be ignored by inline-snapshot and will **not be updated or fixed**, even if they cause tests to fail.

These types are:

- [dirty-equals](#dirty-equals) expressions,
- [dynamic code](#is) inside `Is(...)`,
- [snapshots](#inner-snapshots) inside snapshots and
- [f-strings](#f-strings).

You can also create your own unmanaged types with `@declare_unmanaged`

```
from inline_snapshot import declare_unmanaged, snapshot


@declare_unmanaged
class AllEqual:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return all(o == self.value for o in other)


def test_all_equal():
    assert {"text": "hello", "values": [1, 1, 1]} == snapshot(
        {"text": "hello", "values": AllEqual(snapshot(1))}
    )
```

You have to put `AllEqual` manually into the snapshot and inline-snapshot will not touch it in the future when it has to fix the code, but it will change the value in the snapshot argument of `AllEqual`, because this is another snapshot. This allows you to specify what should be under your control and which code should be controlled and changed by inline-snapshot.

inline-snapshot is able to handle these types within the following containers:

- list
- tuple
- dict
- [namedtuple](https://docs.python.org/3/library/collections.html#collections.namedtuple)
- [dataclass](https://docs.python.org/3/library/dataclasses.html)
- [attrs](https://www.attrs.org/en/stable/index.html)

Other types are converted with a [customizable](../customize_repr/) `repr()` into code. It is not possible to use unmanaged snapshot values within these objects.

### dirty-equals

[dirty-equals](https://dirty-equals.helpmanual.io/latest/) is a library of special objects for comparing types declaratively in unit tests. inline-snapshot supports dirty-equals expressions inside snapshots, making it easier to write snapshots that contain data that varies between test runs, such as timestamps, database IDs, or other runtime values.

To use dirty-equals with inline-snapshot, pull in a compatible version with the `dirty-equals` extra dependency. For example, with Pip:

```
pip install inline-snapshot[dirty-equals]
```

Then you can start using dirty-equals expressions inside snapshots.

For example, say you have a function that returns a dictionary that contains a variable `datetime`. You could initialize a test like this:

```
from inline_snapshot import snapshot
import datetime


def get_data():
    return {
        "date": datetime.datetime.utcnow(),
        "payload": "some data",
    }


def test_function():
    assert get_data() == snapshot()
```

If you use `--inline-snapshot=create`, inline-snapshot will record the current `datetime` in the snapshot:

```
from inline_snapshot import snapshot
import datetime


def get_data():
    return {
        "date": datetime.datetime.utcnow(),
        "payload": "some data",
    }


def test_function():
    assert get_data() == snapshot(
        {"date": datetime.datetime(2024, 3, 14, 0, 0), "payload": "some data"}
    )
```

To avoid the test failing in future runs, replace the `datetime` with [dirty-equals' `IsDatetime()`](https://dirty-equals.helpmanual.io/latest/types/datetime/#dirty_equals.IsDatetime):

```
from inline_snapshot import snapshot
from dirty_equals import IsDatetime
import datetime


def get_data():
    return {
        "date": datetime.datetime.utcnow(),
        "payload": "some data",
    }


def test_function():
    assert get_data() == snapshot(
        {
            "date": IsDatetime(),
            "payload": "some data",
        }
    )
```

Say a different part of the return data changes, such as the `payload` value:

```
from inline_snapshot import snapshot
from dirty_equals import IsDatetime
import datetime


def get_data():
    return {
        "date": datetime.datetime.utcnow(),
        "payload": "data changed for some good reason",
    }


def test_function():
    assert get_data() == snapshot(
        {
            "date": IsDatetime(),
            "payload": "some data",
        }
    )
```

Re-running the test with `--inline-snapshot=fix` will update the snapshot to match the new value of `payload`, while keeping the `date` as a dirty-equals expression:

```
from inline_snapshot import snapshot
from dirty_equals import IsDatetime
import datetime


def get_data():
    return {
        "date": datetime.datetime.utcnow(),
        "payload": "data changed for some good reason",
    }


def test_function():
    assert get_data() == snapshot(
        {
            "date": IsDatetime(),
            "payload": "data changed for some good reason",
        }
    )
```

#### `snapshot()` inside dirty-equals expressions

`snapshot()` can also be used inside dirty-equals containers, such as with [`IsJson()`](https://dirty-equals.helpmanual.io/latest/types/other/#dirty_equals.IsJson):

```
from dirty_equals import IsJson
from inline_snapshot import snapshot


def test_foo():
    assert {"json_data": '{"value": 1}'} == snapshot(
        {"json_data": IsJson(snapshot())}
    )
```

Running this test with `--inline-snapshot=create` will record the snapshot value inside the `IsJson()` call:

```
from dirty_equals import IsJson
from inline_snapshot import snapshot


def test_foo():
    assert {"json_data": '{"value": 1}'} == snapshot(
        {"json_data": IsJson(snapshot({"value": 1}))}
    )
```

The general rule is that functions to which you pass a snapshot can only use `==` (or other snapshot operations) on the value.

Important

You cannot use a snapshot for every dirty-equals argument, but only for those that also support dirty equals values.

### Is(...)

`Is()` can be used to put runtime values inside snapshots. It tells inline-snapshot that the developer wants control over some part of the snapshot.

```
from inline_snapshot import snapshot, Is

current_version = "1.5"


def request():
    return {"data": "page data", "version": current_version}


def test_function():
    assert request() == snapshot(
        {"data": "page data", "version": Is(current_version)}
    )
```

The snapshot does not need to be fixed when `current_version` changes in the future, but `"page data"` will still be fixed if it changes.

`Is()` can also be used when the snapshot is evaluated multiple times, which is useful in loops or parametrized tests.

```
from inline_snapshot import snapshot, Is


def test_function():
    for c in "abc":
        assert [c, "correct"] == snapshot([Is(c), "wrong"])
```

```
from inline_snapshot import snapshot, Is


def test_function():
    for c in "abc":
        assert [c, "correct"] == snapshot([Is(c), "correct"])
```

### inner snapshots

Snapshots can be used inside other snapshots in different use cases.

#### conditional snapshots

It is also possible to use snapshots inside snapshots.

This is useful to describe version specific parts of snapshots by replacing the specific part with `snapshot() if some_condition else snapshot()`. The test has to be executed in each specific condition to fill the snapshots.

The following example shows how this can be used to run a tests with two different library versions:

```
version = 1


def get_schema():
    return [{"name": "var_1", "type": "int"}]
```

```
version = 2


def get_schema():
    return [{"name": "var_1", "type": "string"}]
```

```
from inline_snapshot import snapshot
from my_lib import version, get_schema


def test_function():
    assert get_schema() == snapshot(
        [
            {
                "name": "var_1",
                "type": snapshot("int") if version < 2 else snapshot("string"),
            }
        ]
    )
```

The advantage of this approach is that the test uses always the correct values for each library version.

You can also extract the version logic into its own function.

```
from inline_snapshot import snapshot, Snapshot
from my_lib import version, get_schema


def version_snapshot(v1: Snapshot, v2: Snapshot):
    return v1 if version < 2 else v2


def test_function():
    assert get_schema() == snapshot(
        [
            {
                "name": "var_1",
                "type": version_snapshot(
                    v1=snapshot("int"), v2=snapshot("string")
                ),
            }
        ]
    )
```

#### common snapshot parts

Another use case is the extraction of common snapshot parts into an extra snapshot:

```
from inline_snapshot import snapshot


def some_data(name):
    return {"header": "really long header\n" * 5, "your name": name}


def test_function():

    header = snapshot(
        """\
really long header
really long header
really long header
really long header
really long header
"""
    )

    assert some_data("Tom") == snapshot(
        {
            "header": header,
            "your name": "Tom",
        }
    )

    assert some_data("Bob") == snapshot(
        {
            "header": header,
            "your name": "Bob",
        }
    )
```

This simplifies test data and allows inline-snapshot to update your values if required. It makes also sure that the header is the same in both cases.

### f-strings

*f-strings* are not generated by inline-snapshot, but they can be used in snapshots if you want to replace some dynamic part of a string value.

```
from inline_snapshot import snapshot


def get_error():
    # example code which generates an error message
    return __file__ + ": error at line 5"


def test_get_error():
    assert get_error() == snapshot(f"{__file__}: error at line 5")
```

It is not required to wrap the changed value in `Is(f"...")`, because inline-snapshot knows that *f-strings* are only generated by the developer.

Limitation

inline-snapshot is currently not able to fix the string constants within *f-strings*.

`f"...{var}..."` works **currently** like `Is(f"...{var}...")` and issues a warning if the value changes, giving you the opportunity to fix your f-string.

`f"...{var}..."` will in the **future** work like `f"...{Is(var)}"`. inline-snapshot will then be able to *fix* the string parts within the f-string.

## pytest options

It interacts with the following `--inline-snapshot` flags:

- `create` create a new value if the snapshot value is undefined.
- `fix` record the value parts and store them in the source code if it is different from the current one.
- `update` update parts of the value if their representation has changed. Parts which are replaced with dirty-equals expressions are not updated.
