### Changed

- inline-snapshot uses now `--inline-snapshot=disable` during CI runs by default.
    This improves performance because `snapshot()` is then equal to:
    ```python
    def snapshot(x):
        return x
    ```
    It also has benefits for the accuracy of your tests as it is less likely that inline snapshot will affect your tests in CI.
