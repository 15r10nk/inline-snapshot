<!--
A new scriv changelog fragment.

Uncomment the section that is right (remove the HTML comment wrapper).
-->

<!--
### Removed

- A bullet item for the Removed category.

-->
<!--
### Added

- A bullet item for the Added category.

-->
<!--
### Changed

- A bullet item for the Changed category.

-->
<!--
### Deprecated

- A bullet item for the Deprecated category.

-->
### Fixed

- A snapshot which contains an dirty-equals expression can now be compared multiple times.

    ``` python
    def test_something():
        greeting = "hello"
        for name in ["alex", "bob"]:
            assert (name, greeting) == snapshot((IsString(), "hello"))
    ```

<!--
### Security

- A bullet item for the Security category.

-->
