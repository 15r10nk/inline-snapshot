Default configuration:

``` toml
[tool.inline-snapshot]
hash-length=15
default-flags=["short-report"]
format-command=""

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

* **storage-dir:** allows you to define the directory where inline-snapshot stores data files such as external snapshots.
    By default, it will be `<pytest_config_dir>/.inline-snapshot`,
    where `<pytest_config_dir>` is replaced by the directory containing the Pytest configuration file, if any.
    External snapshots will be stored in the `external` subfolder of the storage directory.
* **format-command:[](){#format-command}** allows you to specify a custom command which is used to format the python code after code is changed.
   ``` toml
   [tool.inline-snapshot]
   format-command="ruff format --stdin-filename {filename}"
   ```
   The placeholder `{filename}` can be used to specify the filename if it is needed to find the correct formatting options for this file.

    !!! important
        The command should **not** format the file on disk. The current file content (with the new code changes) is passed to *stdin* and the formatted content should be written to *stdout*.
