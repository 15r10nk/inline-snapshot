### Fixed

- Fixed customize hook registration to properly check if objects are functions before inspecting the `inline_snapshot_impl` attribute, preventing potential attribute errors when scanning conftest modules.
