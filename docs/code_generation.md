

You can use almost any python data type and also complex values like `datetime.date`, because `repr()` is used to convert the values to source code.
The default `__repr__()` behaviour can be [customized](customize_repr.md).
It might be necessary to import the right modules to match the `repr()` output.

=== "original code"
    <!-- inline-snapshot: first_block outcome-passed=1 outcome-errors=1 -->
    ``` python
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
            "bytes": b"byte abc\n\x16",
        }


    def test_something():
        assert something() == snapshot()
    ```
=== "--inline-snapshot=create"
    <!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
    ``` python hl_lines="18 19 20 21 22 23 24 25 26 27 28"
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
            "bytes": b"byte abc\n\x16",
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
                "bytes": b"byte abc\n\x16",
            }
        )
    ```

The code is generated in the following way:

1. The value is copied with `value = copy.deepcopy(value)` and it is checked if the copied value is equal to the original value.
2. The code is generated with:
    * `repr(value)` (which can be [customized](customize_repr.md))
    * or a special internal implementation for container types to support [unmanaged snapshot values](eq_snapshot.md#unmanaged-snapshot-values).
      This can currently not be customized.
3. Strings which contain newlines are converted to triple quoted strings.

    !!! note
        Missing newlines at start or end are escaped (since 0.4.0).

        === "original code"
            <!-- inline-snapshot: first_block outcome-passed=1 -->
            ``` python
            from inline_snapshot import snapshot


            def test_something():
                assert "first line\nsecond line" == snapshot(
                    """first line
            second line"""
                )
            ```

        === "--inline-snapshot=update"
            <!-- inline-snapshot: update outcome-passed=1 -->
            ``` python hl_lines="6 7 8 9"
            from inline_snapshot import snapshot


            def test_something():
                assert "first line\nsecond line" == snapshot(
                    """\
            first line
            second line\
            """
                )
            ```


4. The new code fragments are formatted with black if it is installed.

    !!! note
        Black is an optional dependency since inline-snapshot v0.19.0.
        You can install it with:
        ``` sh
        pip install inline-snapshot[black]
        ```

5. The whole file is formatted
    * with black if it was formatted with black before.

        !!! note
            The black formatting of the whole file could not work for the following reasons:

            1. black is configured with cli arguments and not in a configuration file.<br>
               **Solution:** configure black in a [configuration file](https://black.readthedocs.io/en/stable/usage_and_configuration/the_basics.html#configuration-via-a-file)
            2. inline-snapshot uses a different black version.<br>
               **Solution:** specify which black version inline-snapshot should use by adding black with a specific version to your dependencies.
            3. black is not installed. Black is an optional dependency since inline-snapshot v0.19.0

    * or with the [format-command][format-command] if you defined one.
