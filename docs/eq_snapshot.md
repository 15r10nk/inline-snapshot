## General

A snapshot can be compared against any value with `==`.
The value can be recorded with `--inline-snapshot=create` if the snapshot is empty.

Example:

=== "original code"
    <!-- inline-snapshot: outcome-passed=1 outcome-errors=1 -->
    ```python
    def test_something():
        assert 2 + 2 == snapshot()
    ```

=== "--inline-snapshot=create"
    <!-- inline-snapshot: create -->
    ```python
    def test_something():
        assert 2 + 2 == snapshot(4)
    ```

=== "value changed"
    <!-- inline-snapshot: outcome-passed=1 outcome-errors=1 -->
    ```python
    def test_something():
        assert 2 + 3 == snapshot(4)
    ```

=== "--inline-snapshot=fix"
    <!-- inline-snapshot: create -->
    ```python
    def test_something():
        assert 2 + 2 == snapshot(4)
    ```

The value can later be changed with `--inline-snapshot=fix` if the value the snapshot is compared with has changed.

It might be, that larger snapshots with many lists and dictionaries contain some values which change frequently and are not relevant for the test.

Example:

=== "original code"
    <!-- inline-snapshot: outcome-passed=1 outcome-errors=1 -->
    ```python
    from inline_snapshot import snapshot
    import datetime


    def get_data():
        return {
            "date": datetime.datetime.now(),
            "payload": "some data",
        }


    def test_function():
        assert get_data() == snapshot()
    ```

=== "--inline-snapshot=create"
    <!-- inline-snapshot: create -->
    ```python
    from inline_snapshot import snapshot
    import datetime


    def get_data():
        return {
            "date": datetime.datetime.now(),
            "payload": "some data",
        }


    def test_function():
        assert get_data() == snapshot(
            {
                "date": datetime.datetime(2024, 3, 27, 18, 7, 57, 198999),
                "payload": "some data",
            }
        )
    ```

inline-snapshot tries to change only the values which it has to change in order to make the equality comparison pass.
This allows to replace parts of the snapshot with expressions with a special `==` implementation like [dirty-equals](https://dirty-equals.helpmanual.io/latest/).
This expressions are preserved as long as the `==` comparison with them is `True`.

Example:

=== "using IsDatetime()"
    <!-- inline-snapshot: outcome-passed=1 -->
    ```python hl_lines="16"
    from inline_snapshot import snapshot
    from dirty_equals import IsDatetime
    import datetime


    def get_data():
        return {
            "date": datetime.datetime.now(),
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

=== "changed data"
    <!-- inline-snapshot: outcome-passed=1 -->
    ```python hl_lines="9"
    from inline_snapshot import snapshot
    from dirty_equals import IsDatetime
    import datetime


    def get_data():
        return {
            "date": datetime.datetime.now(),
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
    <!-- inline-snapshot: fix -->
    ```python
    from inline_snapshot import snapshot
    from dirty_equals import IsDatetime
    import datetime


    def get_data():
        return {
            "date": datetime.datetime.now(),
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


## pytest options

It interacts with the following `--inline-snapshot` flags:

- `create` create a new value if the snapshot value is undefined.
- `fix` record the new value and store it in the source code if it is different from the current one.
- `update` update update the value if the representation has changed.
