Default configuration:

``` toml
[tool.inline-snapshot]
hash-length=15
default-flags=["short-report"]

[tool.inline-snapshot.shortcuts]
review=["review"]
fix=["create","fix"]
```

* **hash-length:** specifies the length of the hash used by `external()` in the code representation.
    This does not affect the hash length used to store the data.
    The hash should be long enough to avoid hash collisions.
* **default-flags:** defines which flags should be used if there are no flags specified with `--inline-snapshot=...`.
    You can also use the environment variable `INLINE_SNAPSHOT_DEFAULT_FLAGS=...` to specify the flags and to override those in the configuration file.

* **shortcuts:** allows you to define custom commands to simplify your workflows.
    `--fix` and `--review` are defined by default, but this configuration can be changed to fit your needs.
