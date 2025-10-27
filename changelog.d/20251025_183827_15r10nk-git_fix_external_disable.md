### Changed

- **BREAKING CHANGE:** An exception is now raised when you use `external()` in files that are not inside your `tests/` directory (or any other directory that you can configure with [tool.inline-snapshot.test-dir](https://15r10nk.github.io/inline-snapshot/latest/configuration/#test-dir)).

- Users are now notified if they use the same UUID for multiple external snapshots, which can happen when copying one test as a template for a new test. The snapshots should be reset to an empty `external()` and recreated with inline-snapshot.

### Fixed

- The lookup for external snapshots has been improved ([#292](https://github.com/15r10nk/inline-snapshot/issues/292)).
