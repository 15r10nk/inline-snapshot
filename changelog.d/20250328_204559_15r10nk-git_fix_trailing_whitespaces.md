### Changed

- trailing white spaces in multi-line strings are now terminated with an `\n\`.
    ``` python
    def test_something():
        assert "a   \nb\n" == snapshot(
            """\
    a   \n\
    b
    """
        )
    ```
