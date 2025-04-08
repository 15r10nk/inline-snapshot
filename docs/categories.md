
Each snapshot change is assigned to a different category. This is done because inline-snapshot supports more than just `==` checks.

There are changes which:

* [create](#create) new snapshot values
* [fix](#fix) your tests
* [update](#update) only the syntax to a new representation
* [trim](#trim) unused pieces from your snapshots

*Create* and *fix* are mainly used, but it is good to know what type of change you are approving, because it helps with the decision if this changes should be applied.


## Categories

### Create

These changes are made when new snapshots are created.

The result of each comparison is `True`, which allows to run the whole test to fill all new snapshots with values.

Example:

<div class="grid" markdown>

<!-- inline-snapshot: first_block outcome-passed=1 outcome-errors=1 -->
``` python
from inline_snapshot import snapshot


def test_something():
    assert 5 == snapshot()

    assert 5 <= snapshot()

    assert 5 in snapshot()

    s = snapshot()
    assert 5 == s["key"]
```

<!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
``` python hl_lines="5 7 9 11"
from inline_snapshot import snapshot


def test_something():
    assert 5 == snapshot(5)

    assert 5 <= snapshot(5)

    assert 5 in snapshot([5])

    s = snapshot({"key": 5})
    assert 5 == s["key"]
```

</div>

### Fix

These changes are made when the snapshots comparison does not return `True` any more (depending on the operation `==`, `<=`, `in`).
The result of each comparison is `True` if you change something from this category, which allows to run the whole test and to fix other snapshots.

<div class="grid" markdown>

<!-- inline-snapshot: first_block outcome-failed=1 outcome-errors=1 -->
``` python
from inline_snapshot import snapshot


def test_something():
    assert 8 == snapshot(5)

    assert 8 <= snapshot(5)

    assert 8 in snapshot([5])

    s = snapshot({"key": 5})
    assert 8 == s["key"]
```

<!-- inline-snapshot: fix outcome-passed=1 outcome-errors=1 -->
``` python hl_lines="5 7 9 11"
from inline_snapshot import snapshot


def test_something():
    assert 8 == snapshot(8)

    assert 8 <= snapshot(8)

    assert 8 in snapshot([5, 8])

    s = snapshot({"key": 8})
    assert 8 == s["key"]
```

</div>


!!! info
    The main reason for the different categories is to make the number of changes in the **fix** category as small as possible.
    The changes in the **fix** category are the only changes which change the value of the snapshots and should be reviewed carefully.




### Trim

These changes are made when parts of the snapshots are removed which are no longer needed, or if limits can be reduced.

<div class="grid" markdown>

<!-- inline-snapshot: first_block outcome-passed=1 -->
``` python
from inline_snapshot import snapshot


def test_something():
    assert 2 <= snapshot(8)

    assert 8 in snapshot([5, 8])

    s = snapshot({"key1": 1, "key2": 2})
    assert 2 == s["key2"]
```

<!-- inline-snapshot: trim outcome-passed=1 -->
``` python hl_lines="5 7 9"
from inline_snapshot import snapshot


def test_something():
    assert 2 <= snapshot(2)

    assert 8 in snapshot([8])

    s = snapshot({"key2": 2})
    assert 2 == s["key2"]
```

</div>

There might be problems in cases where you use the same snapshot in different tests, run only one test and trim the snapshot with `pytest -k test_a --inline-snapshot=trim` in this case:

<div class="grid" markdown>

<!-- todo-inline-snapshot: first_block outcome-passed=2 -->
``` python
from inline_snapshot import snapshot

s = snapshot(5)


def test_a():
    assert 2 <= s


def test_b():
    assert 5 <= s
```

<!-- todo-inline-snapshot: trim outcome-passed=2 -->
``` python hl_lines="1"
from inline_snapshot import snapshot

s = snapshot(2)


def test_a():
    assert 2 <= s


def test_b():
    assert 5 <= s
```

</div>

The value of the snapshot is reduced to `2`, because `test_a()` was the only test running and inline-snapshot does not know about `5 <= s`.
It is recommended to use trim only if you run your complete test suite.

### Update

Changes in the update category do not change the value in the code, just the representation. The reason might be that `#!python repr()` of the object has changed or that inline-snapshot provides some new logic which changes the representation. Like with the strings in the following example:


=== "original"
    <!-- inline-snapshot: first_block outcome-passed=1 -->
    ``` python
    from inline_snapshot import snapshot


    class Vector:
        def __init__(self, x, y):
            self.x = x
            self.y = y

        def __eq__(self, other):
            if not isinstance(other, Vector):
                return NotImplemented
            return self.x == other.x and self.y == other.y

        def __repr__(self):
            # return f"Vector(x={self.x}, y={self.y})"
            return f"Vector({self.x}, {self.y})"


    def test_something():
        assert "a\nb\nc\n" == snapshot("a\nb\nc\n")

        assert 5 == snapshot(4 + 1)

        assert Vector(1, 2) == snapshot(Vector(x=1, y=2))
    ```

=== "--inline-snapshot=update"

    <!-- inline-snapshot: update outcome-passed=1 -->
    ``` python hl_lines="20 21 22 23 24 25 26 28 30"
    from inline_snapshot import snapshot


    class Vector:
        def __init__(self, x, y):
            self.x = x
            self.y = y

        def __eq__(self, other):
            if not isinstance(other, Vector):
                return NotImplemented
            return self.x == other.x and self.y == other.y

        def __repr__(self):
            # return f"Vector(x={self.x}, y={self.y})"
            return f"Vector({self.x}, {self.y})"


    def test_something():
        assert "a\nb\nc\n" == snapshot(
            """\
    a
    b
    c
    """
        )

        assert 5 == snapshot(5)

        assert Vector(1, 2) == snapshot(Vector(1, 2))
    ```


The approval of this type of changes is easier, because inline-snapshot assures that the value has not changed.

It is not necessary, but recommended to make these changes for the following reason:

The goal of inline-snapshot is to generate the values for you in the correct format so that no manual editing is required.
This improves your productivity and saves time.
Keep in mind that any changes you make to your snapshots will likely need to be redone if your program's behaviour (and expected values) change.
Inline-snapshot uses the *update* category to let you know when it has a different opinion than you about how the code should look.
You can agree with inline-snapshot and accept the changes or you can use one of the following options to tell inline-snapshot what the code should look like:

1. change the `__repr__` implementation of your object or use [customize repr](customize_repr.md) if the class is not part of your codebase.

2. define a [format-command](configuration.md#format-command) if another tool has a different opinion about how your code should look. Inline-snapshot will apply this formatting before reporting an update.

3. inline-snapshot manages everything within `snapshot(...)`, but you can take control by using [Is()](eq_snapshot.md#is) in cases where you want to use custom code (like local variables) in your snapshots.

4. you can also open an [issue](https://github.com/15r10nk/inline-snapshot/issues?q=is%3Aissue%20state%3Aopen%20label%3Aupdate_related) if you have a specific problem with the way inline-snapshot generates the code.
