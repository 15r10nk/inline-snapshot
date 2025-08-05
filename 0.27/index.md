# Welcome to inline-snapshot

inline-snapshot can be used for different things:

- golden master/approval/snapshot testing. The idea is that you have a function with a currently unknown result and you want to write a test, which ensures that the result does not change during refactoring.
- Compare things which are complex like lists with lot of numbers or complex data structures.
- Things which might change during the development like error messages.

`inline-snapshot` automates the process of recording, storing and updating the value you want to compare with. The value is converted with `repr()` and stored in the source file as argument of the `snapshot()` function.

News

Hello, I would like to inform you about some changes.

I have started to offer [insider](https://15r10nk.github.io/inline-snapshot/latest/insiders/) features for inline-snapshot. I will only release features as insider features if they will not cause problems for you when used in an open source project.

I hope this will allow me to spend more time working on open source projects. Thank you for using inline-snapshot, the future will be 🚀.

The first feature is that inline-snapshot can now also fix normal assertions which do not use `snapshot()` like:

```
assert 1 + 1 == 3

```

You can learn [here](fix_assert/) more about this feature.

## Usage

You can use `snapshot()` instead of the value which you want to compare with and run the tests to record the correct values.

```
from inline_snapshot import snapshot


def something():
    return 1548 * 18489


def test_something():
    assert something() == snapshot()

```

```
from inline_snapshot import snapshot


def something():
    return 1548 * 18489


def test_something():
    assert something() == snapshot(28620972)

```

Your tests will break, if you change your code by adding `// 18`. Maybe that is correct and you should fix your code, or your code is correct and you want to update your test results.

```
from inline_snapshot import snapshot


def something():
    return (1548 * 18489) // 18


def test_something():
    assert something() == snapshot(28620972)

```

```
from inline_snapshot import snapshot


def something():
    return (1548 * 18489) // 18


def test_something():
    assert something() == snapshot(1590054)

```

Please verify the new results. `git diff` will give you a good overview over all changed results. Use `pytest -k test_something --inline-snapshot=fix` if you only want to change one test.

## Supported operations

You can use `snapshot(x)` like you can use `x` in your assertion with a limited set of operations:

- [`value == snapshot()`](eq_snapshot/) to compare with something,
- [`value <= snapshot()`](cmp_snapshot/) to ensure that something gets smaller/larger over time (number of iterations of an algorithm you want to optimize for example),
- [`value in snapshot()`](in_snapshot/) to check if your value is in a known set of values,
- [`snapshot()[key]`](getitem_snapshot/) to generate new sub-snapshots on demand.

Warning

One snapshot can only be used with one operation. The following code will not work:

```
from inline_snapshot import snapshot


def test_something():
    s = snapshot(5)
    assert 5 <= s
    assert 5 == s


# Error:
# >       assert 5 == s
# E       TypeError: This snapshot cannot be use with `==`, because it was previously used with `x <= snapshot`

```

## Supported usage

It is possible to place `snapshot()` anywhere in the tests and reuse it multiple times.

```
from inline_snapshot import snapshot


def something():
    return 21 * 2


result = snapshot()


def test_something():
    ...
    assert something() == result


def test_something_again():
    ...
    assert something() == result

```

```
from inline_snapshot import snapshot


def something():
    return 21 * 2


result = snapshot(42)


def test_something():
    ...
    assert something() == result


def test_something_again():
    ...
    assert something() == result

```

`snapshot()` can also be used in loops:

```
from inline_snapshot import snapshot


def test_loop():
    for name in ["Mia", "Eva", "Leo"]:
        assert len(name) == snapshot()

```

```
from inline_snapshot import snapshot


def test_loop():
    for name in ["Mia", "Eva", "Leo"]:
        assert len(name) == snapshot(3)

```

or passed as an argument to a function:

```
from inline_snapshot import snapshot


def check_string_len(string, snapshot_value):
    assert len(string) == snapshot_value


def test_string_len():
    check_string_len("abc", snapshot())
    check_string_len("1234", snapshot())
    check_string_len(".......", snapshot())

```

```
from inline_snapshot import snapshot


def check_string_len(string, snapshot_value):
    assert len(string) == snapshot_value


def test_string_len():
    check_string_len("abc", snapshot(3))
    check_string_len("1234", snapshot(4))
    check_string_len(".......", snapshot(7))

```

## Feedback

inline-snapshot provides some advanced ways to work with snapshots.

I would like to know how these features are used to further improve this small library. Let me know if you've found interesting use cases for this library via [twitter](https://twitter.com/15r10nk), [fosstodon](https://fosstodon.org/deck/@15r10nk) or in the github [discussions](https://github.com/15r10nk/inline-snapshot/discussions/new?category=show-and-tell).

## Sponsors

I would like to thank my sponsors. Without them, I would not be able to invest so much time in my projects.

### Bronze sponsor 🥉

## Issues

If you encounter any problems, please [report an issue](https://github.com/15r10nk/inline-snapshot/issues) along with a detailed description.
