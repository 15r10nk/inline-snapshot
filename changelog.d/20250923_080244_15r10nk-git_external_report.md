### Changed

- `Example.run_inline` can now be used with `["--inline-snapshot=disable"]`.

### Fixed

- `--inline-snapshot=report` now shows the same changes for external snapshots as `--inline-snapshot=review` ([#298](https://github.com/15r10nk/inline-snapshot/issues/298)).
- Fixed a crash when generating reports for `external_file("some_non_existing_file.txt")`.
