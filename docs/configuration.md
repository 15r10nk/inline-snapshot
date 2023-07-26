

Default configuration:

``` toml
[tool.inline-snapshot]
hash-length=15
```

* *hash-length* specifies the length of the hash used by `external()` in the code representation.
    This does not affect the hash length used to store the data.
    The hash should be long enough to avoid hash collisions.
