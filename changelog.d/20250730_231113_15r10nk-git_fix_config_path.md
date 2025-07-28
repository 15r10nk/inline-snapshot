### Changed

- You now have to specify `test-dir` in your pyproject.toml when you save your tests in a folder other than `tests/` in your project root (#272).

### Fixed

- `pyproject.toml` is now also located based on the current directory and the `pytest-root`, which solves problems when you use inline-snapshot with uv-workspaces (#272).
