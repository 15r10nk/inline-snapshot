### Added

- Added `Builder.create_set()` for creating set expressions in customization
  functions.

### Fixed

- Fixed set snapshot serialization to be deterministic for partially ordered values
  such as incomparable `frozenset` members.
