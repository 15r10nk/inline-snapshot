### Fixed

- fixed string formatting with black which caused invalid snapshots ([#301](https://github.com/15r10nk/inline-snapshot/issues/301))

    ``` python
    assert " a " == snapshot("a")
    ```
