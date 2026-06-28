### Changed

- Removed the `tool.inline-snapshot.test-dir` configuration option.
- inline-snapshot now tracks source files that use `external()` in `.inline-snapshot/external_files.txt` (inside `storage-dir`) and uses this tracked list to detect and trim unused external snapshots.
