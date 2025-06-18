## General

It is possible to add support for your custom file formats to inline-snapshot.
All what is needed is to implement some `encode/decode` functions.
The following examples show the implementation of the builtin formats.

=== "text"

    ``` python
    --8 < --"src/inline_snapshot/_external/_format/_text.py"
    ```

=== "binary"

    ``` python
    --8 < --"src/inline_snapshot/_external/_format/_binary.py"
    ```

=== "json"

    ``` python
    --8 < --"src/inline_snapshot/_external/_format/_json.py"
    ```

## Reference

::: inline_snapshot
    options:
      heading_level: 3
      members: [register_format,register_format_alias,Format]
      show_root_heading: false
      show_bases: false
      show_source: false
