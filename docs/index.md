
--8<-- "README.md:Header"


# Welcome to inline-snapshot

inline-snapshot can be used for different things:

* golden master/approval/snapshot testing.
  The idea is that you have a function with a currently unknown result and you want to write a tests, which ensures that the result does not change during refactoring.
* Compare things which are complex like lists with lot of numbers or complex data structures.
* Things which might change during the development like error messages.


`inline-snapshot` automates the process of recording, storing and updating the value you want to compare with.
The value is converted with `repr()` and stored in the source file as argument of the `snapshot()` function.

## Usage

You can use `snapshot()` instead of the value which you want to compare with and run the tests to record the correct values.

=== "original code"

    <!-- inline-snapshot: outcome-passed=1 outcome-errors=1 -->
    ```python
    from inline_snapshot import snapshot


    def something():
        return 1548 * 18489


    def test_something():
        assert something() == snapshot()
    ```


=== "--inline-snapshot=create"

    <!-- inline-snapshot: create outcome-passed=1 -->
    ```python
    from inline_snapshot import snapshot


    def something():
        return 1548 * 18489


    def test_something():
        assert something() == snapshot(28620972)
    ```

Your tests will break, if you change your code by adding `// 18`.
Maybe that is correct and you should fix your code, or
your code is correct and you want to update your test results.

=== "changed code"
    <!-- inline-snapshot: outcome-failed=1 -->
    ```python
    def something():
        return (1548 * 18489) // 18


    def test_something():
        assert something() == snapshot(28620972)
    ```


=== "--inline-snapshot=fix"
    <!-- inline-snapshot: fix outcome-passed=1 -->
    ```python
    def something():
        return (1548 * 18489) // 18


    def test_something():
        assert something() == snapshot(1590054)
    ```

Please verify the new results. `git diff` will give you a good overview over all changed results.
Use `pytest -k test_something --inline-snapshot=fix` if you only want to change one test.


## Supported operations

You can use `snapshot(x)` like you can use `x` in your assertion with a limited set of operations:

- [`value == snapshot()`](eq_snapshot.md) to compare with something,
- [`value <= snapshot()`](cmp_snapshot.md) to ensure that something gets smaller/larger over time (number of iterations of an algorithm you want to optimize for example),
- [`value in snapshot()`](in_snapshot.md) to check if your value is in a known set of values,
- [`snapshot()[key]`](getitem_snapshot.md) to generate new sub-snapshots on demand.

!!! warning
    One snapshot can only be used with one operation.
    The following code will not work:
    <!-- inline-snapshot: show_error outcome-failed=1 -->
    ``` python
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


=== "original code"

    <!-- inline-snapshot: outcome-passed=2 -->
    ```python
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

=== "--inline-snapshot=create"

    <!-- inline-snapshot: create outcome-passed=2 -->
    ```python
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

=== "original code"
    <!-- inline-snapshot: outcome-passed=1 outcome-errors=1 -->
    ```python
    def test_loop():
        for name in ["Mia", "Eva", "Leo"]:
            assert len(name) == snapshot()
    ```
=== "--inline-snapshot=create"
    <!-- inline-snapshot: create outcome-passed=1 -->
    ```python
    def test_loop():
        for name in ["Mia", "Eva", "Leo"]:
            assert len(name) == snapshot(3)
    ```

or passed as an argument to a function:


=== "original code"
    <!-- inline-snapshot: outcome-passed=1 outcome-errors=1 -->
    ```python
    def check_string_len(string, snapshot_value):
        assert len(string) == snapshot_value


    def test_string_len():
        check_string_len("abc", snapshot())
        check_string_len("1234", snapshot())
        check_string_len(".......", snapshot())
    ```

=== "--inline-snapshot=create"
    <!-- inline-snapshot: create outcome-passed=1 -->
    ``` python
    def check_string_len(string, snapshot_value):
        assert len(string) == snapshot_value


    def test_string_len():
        check_string_len("abc", snapshot(3))
        check_string_len("1234", snapshot(4))
        check_string_len(".......", snapshot(7))
    ```



## Code generation

You can use almost any python datatype and also complex values like `datatime.date`, because `repr()` is used to convert the values to a source code.
It might be necessary to import the right modules to match the `repr()` output.

=== "original code"
    <!-- inline-snapshot: outcome-passed=1 outcome-errors=1 -->
    ```python
    from inline_snapshot import snapshot
    import datetime


    def something():
        return {
            "name": "hello",
            "one number": 5,
            "numbers": list(range(10)),
            "sets": {1, 2, 15},
            "datetime": datetime.date(1, 2, 22),
            "complex stuff": 5j + 3,
            "bytes": b"fglecg\n\x16",
        }


    def test_something():
        assert something() == snapshot()
    ```
=== "--inline-snapshot=create"
    <!-- inline-snapshot: create outcome-passed=1 -->
    ```python
    from inline_snapshot import snapshot
    import datetime


    def something():
        return {
            "name": "hello",
            "one number": 5,
            "numbers": list(range(10)),
            "sets": {1, 2, 15},
            "datetime": datetime.date(1, 2, 22),
            "complex stuff": 5j + 3,
            "bytes": b"fglecg\n\x16",
        }


    def test_something():
        assert something() == snapshot(
            {
                "name": "hello",
                "one number": 5,
                "numbers": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                "sets": {1, 2, 15},
                "datetime": datetime.date(1, 2, 22),
                "complex stuff": (3 + 5j),
                "bytes": b"fglecg\n\x16",
            }
        )
    ```

The code is generated in the following way:

1. The value is copied with `value = copy.deepcopy(value)`
2. The code is generated with `repr(value)`
3. Strings which contain newlines are converted to triple quoted strings.

    !!! note
        Missing newlines at start or end are escaped (since 0.4.0).

        === "original code"
            <!-- inline-snapshot: outcome-passed=1 -->
            ``` python
            def test_something():
                assert "first line\nsecond line" == snapshot(
                    """first line
            second line"""
                )
            ```

        === "--inline-snapshot=update"
            <!-- inline-snapshot: update outcome-passed=1 -->
            ``` python
            def test_something():
                assert "first line\nsecond line" == snapshot(
                    """\
            first line
            second line\
            """
                )
            ```


4. The code is formatted with black.

    !!! note
        The black formatting of the whole file could not work for the following reasons:

        1. black is configured with cli arguments and not in a configuration file.<br>
           **Solution:** configure black in a [configuration file](https://black.readthedocs.io/en/stable/usage_and_configuration/the_basics.html#configuration-via-a-file)
        2. inline-snapshot uses a different black version.<br>
           **Solution:** specify which black version inline-snapshot should use by adding black with a specific version to your dependencies.

5. The whole file is formatted with black if it was formatted before.

--8<-- "README.md:Feedback"
