## General

A snapshot can be compared against any value with `<=` or `>=`.
This can be used to create a upper/lower bound for some result.
The snapshot value can be trimmed to the lowest/largest valid value.

Example:

=== "original code"
    <!-- inline-snapshot: first_block outcome-passed=1 outcome-errors=1 -->
    ``` python
    from inline_snapshot import snapshot


    def gcd(x, y):
        iterations = 0
        if x > y:
            small = y
        else:
            small = x
        for i in range(1, small + 1):
            iterations += 1
            if (x % i == 0) and (y % i == 0):
                gcd = i

        return gcd, iterations


    def test_gcd():
        result, iterations = gcd(12, 18)

        assert result == snapshot()
        assert iterations <= snapshot()
    ```

=== "--inline-snapshot=create"
    <!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
    ``` python hl_lines="21 22"
    from inline_snapshot import snapshot


    def gcd(x, y):
        iterations = 0
        if x > y:
            small = y
        else:
            small = x
        for i in range(1, small + 1):
            iterations += 1
            if (x % i == 0) and (y % i == 0):
                gcd = i

        return gcd, iterations


    def test_gcd():
        result, iterations = gcd(12, 18)

        assert result == snapshot(6)
        assert iterations <= snapshot(12)
    ```

=== "optimized code "
    <!-- inline-snapshot: outcome-passed=1 -->
    ``` python hl_lines="5 7 9 10"
    from inline_snapshot import snapshot


    def gcd(x, y):
        # use Euclidean Algorithm
        iterations = 0
        while y:
            iterations += 1
            x, y = y, x % y
        return abs(x), iterations


    def test_gcd():
        result, iterations = gcd(12, 18)

        assert result == snapshot(6)
        assert iterations <= snapshot(12)
    ```

=== "--inline-snapshot=trim"
    <!-- inline-snapshot: trim outcome-passed=1 -->
    ``` python hl_lines="17"
    from inline_snapshot import snapshot


    def gcd(x, y):
        # use Euclidean Algorithm
        iterations = 0
        while y:
            iterations += 1
            x, y = y, x % y
        return abs(x), iterations


    def test_gcd():
        result, iterations = gcd(12, 18)

        assert result == snapshot(6)
        assert iterations <= snapshot(3)
    ```

!!! warning
    This should not be used to check for any flaky values like the runtime of some code, because it will randomly break your tests.

The same snapshot value can also be used in multiple assertions.

=== "original code"
    <!-- inline-snapshot: first_block outcome-passed=1 outcome-errors=1 -->
    ``` python
    from inline_snapshot import snapshot


    def test_something():
        value = snapshot()

        assert 5 <= value
        assert 6 <= value
    ```
=== "--inline-snapshot=create"
    <!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
    ``` python hl_lines="5"
    from inline_snapshot import snapshot


    def test_something():
        value = snapshot(6)

        assert 5 <= value
        assert 6 <= value
    ```

## pytest options

It interacts with the following `--inline-snapshot` flags:

- `create` create a new value if the snapshot value is undefined.
- `fix` record the new value and store it in the source code if it is contradicts the comparison.
- `trim` record the new value and store it in the source code if it is more strict than the old one.
