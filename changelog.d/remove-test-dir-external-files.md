### Changed

- inline-snapshot now tracks source files that use `external()` in `.inline-snapshot/files_using_external.txt` (inside `storage-dir`) and uses this tracked list to detect and trim unused external snapshots.
- The `tool.inline-snapshot.test-dir` configuration option is only used as a compatibility fallback when `files_using_external.txt` does not exist yet.
