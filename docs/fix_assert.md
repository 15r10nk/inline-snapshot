## General


!!! info

    The following feature is available for [insider](insiders.md) :heart: only
    and requires cpython>=3.11.


The `snapshot()` function provides a lot of flexibility, but there is a easier way for simple assertion.
You can write a normal assertion and use `...` where inline-snapshot should create the new value, like in the following example.

=== "original code"
    <!-- inline-snapshot: requires_assert first_block outcome-failed=1 outcome-errors=1 -->
    ``` python
    def test_assert():
        assert 1 + 1 == ...
    ```

=== "--inline-snapshot=create"
    <!-- inline-snapshot: create requires_assert outcome-failed=1 outcome-errors=1 -->
    ``` python hl_lines="2"
    def test_assert():
        assert 1 + 1 == 2
    ```

inline-snapshot will detect these failures and will replace `...` with the correct value.

It is also possible to fix existing values.

=== "original code"
    <!-- inline-snapshot: requires_assert first_block outcome-failed=1 outcome-errors=1 -->
    ``` python
    def test_assert():
        assert 1 + 1 == 5
    ```

=== "--inline-snapshot=fix-assert"
    <!-- inline-snapshot: requires_assert outcome-passed=1 -->
    ``` python hl_lines="2"
    def test_assert():
        assert 1 + 1 == 2
    ```

This is especially useful to fix values in existing codebases where `snapshot()` is currently not used.

The logic to create/fix the assertions is the same like for snapshots, but there are rules which specify which side of the `==` should be fixed.
This allows assertions like `#!python assert 5 == 1 + 2` to be fixed and prevents inline-snapshot to try to fix code like `#!python assert f1() == f2()`.

The rule is that exactly one side of the equation must be a *value expression*, which is defined as follows:

* a constant
* a list/tuple/dict/set of *value expressions*
* a constructor call such as `T(...arguments)`
    * where the arguments are *value expressions*
    * and `T` is a type (which excludes function calls)



## Limitations

* `cpython>=3.11` is required to create/fix assertions.
* It can only fix the first failing assertion in a test.
  You need to run your tests a multiple times to fix the remaining ones.
* It is not possible to fix values where inline-snapshot did not know which side of the equal sign should be fixed.
  You can use `snapshot()` in this case to make this clear.



## pytest options

It interacts with the following `--inline-snapshot` flags:

- `create` create a new value where `...` is used.
- `fix-assert` fix the value if the assertion fails.

    !!! note

        fix-assert is used to distinguisch between snapshot fixes and assertion fixes without snapshot().
        This should help in deciding whether some fixes should be approved.
        Fixing normal assertions is inherently more complicated because these assertions are written by a human without the intention of being automatically fixed.
        Separating the two helps in approving the changes.
