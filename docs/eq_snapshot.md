## General

A snapshot can be compared with any value using `==`.
The value can be recorded with `--inline-snapshot=create` if the snapshot is empty.
The value can later be changed with `--inline-snapshot=fix` if the value the snapshot is compared with has changed.

Example:

=== "original code"
    <!-- inline-snapshot: first_block outcome-passed=1 outcome-errors=1 -->
    ``` python
    def test_something():
        assert 2 + 4 == snapshot()
    ```

=== "--inline-snapshot=create"
    <!-- inline-snapshot: create outcome-passed=1 -->
    ``` python hl_lines="2"
    def test_something():
        assert 2 + 4 == snapshot(6)
    ```

=== "value changed"
    <!-- inline-snapshot: outcome-failed=1 -->
    ``` python hl_lines="2"
    def test_something():
        assert 2 + 40 == snapshot(4)
    ```

=== "--inline-snapshot=fix"
    <!-- inline-snapshot: fix outcome-passed=1 -->
    ``` python hl_lines="2"
    def test_something():
        assert 2 + 40 == snapshot(42)
    ```


## dirty-equals

It might be, that larger snapshots with many lists and dictionaries contain some values which change frequently and are not relevant for the test.
They might be part of larger data structures and be difficult to normalize.

Example:

=== "original code"
    <!-- inline-snapshot: first_block outcome-passed=1 outcome-errors=1 -->
    ``` python
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

=== "--inline-snapshot=create"
    <!-- inline-snapshot: create outcome-passed=1 -->
    ``` python hl_lines="13 14 15"
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

inline-snapshot tries to change only the values that it needs to change in order to pass the equality comparison.
This allows to replace parts of the snapshot with [dirty-equals](https://dirty-equals.helpmanual.io/latest/) expressions.
This expressions are preserved as long as the `==` comparison with them is `True`.

Example:

=== "using IsDatetime()"
    <!-- inline-snapshot: first_block outcome-passed=1 -->
    ``` python
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

=== "changed payload"
    <!-- inline-snapshot: outcome-failed=1 -->
    ``` python hl_lines="9"
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


=== "--inline-snapshot=fix"
    <!-- inline-snapshot: fix outcome-passed=1 -->
    ``` python hl_lines="17"
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

!!! note
    The current implementation looks only into lists, dictionaries and tuples and not into the representation of other data structures.

## pytest options

It interacts with the following `--inline-snapshot` flags:

- `create` create a new value if the snapshot value is undefined.
- `fix` record the value parts and store them in the source code if it is different from the current one.
- `update` update parts of the value if their representation has changed.
  Parts which are replaced with dirty-equals expressions are not updated.
