### Changed

- `External.run_inline()` now uses the same logic as `External.run_pytest`.

### Fixed

- inline-snapshot now supports different Python file encodings and recognizes encoding comments such as `# -*- coding: windows-1251 -*-` ([#305](https://github.com/15r10nk/inline-snapshot/issues/305)).
