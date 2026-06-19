# AGENTS.md

## Project Overview

`inline-snapshot` is a Python snapshot/approval testing library for pytest. Its core feature is storing expected values directly in source code through APIs such as `snapshot()`, `snapshot_arg()`, `external()`, and `outsource()`. The package also ships a pytest plugin that can report, review, create, update, trim, and fix snapshots.

The project supports Python 3.9 through 3.14 and PyPy where possible. CI runs across Linux, macOS, Windows, CPython, PyPy, and both Pydantic 1 and 2 dependency sets.

## Repository Layout

- `src/inline_snapshot/`: package source.
- `src/inline_snapshot/pytest_plugin.py`: pytest entry point and CLI flag handling.
- `src/inline_snapshot/_inline_snapshot.py`, `_snapshot_arg.py`, `_get_snapshot_value.py`: main public snapshot behavior.
- `src/inline_snapshot/_snapshot/`: snapshot value implementations such as equality, dict, min/max, collection, and undecided values.
- `src/inline_snapshot/_customize/`: code-generation customization support.
- `src/inline_snapshot/_external/`: external snapshot files, formats, storage, diffing, and outsourcing.
- `src/inline_snapshot/plugin/`: first-party plugin hook specification and default plugin.
- `src/inline_snapshot/testing/_example.py`: preferred test harness for new behavior tests.
- `tests/`: pytest suite. Adapter tests live in `tests/adapter/`; external snapshot tests live in `tests/external/`.
- `docs/`: MkDocs Material documentation.
- `changelog.d/`: scriv changelog fragments. Do not edit `CHANGELOG.md` directly.
- `.github/workflows/ci.yml`: CI matrix and coverage enforcement.

## Development Commands

The project is configured around `uv` and Hatch.

- Install/run ad hoc commands: `uv run --group dev ...`
- Run the normal test suite: `uv run --group dev pytest`
- Run a focused test: `uv run --group dev pytest tests/test_file.py::test_name`
- Run tests with coverage locally: `hatch test -acp`
- Run the full Hatch test matrix: `hatch test`
- Run one Hatch Python version with pytest args: `hatch test -py 3.10 -- --sw`
- Run mypy like CI: `uv run --with pip --group dev -p 3.12 mypy --non-interactive --install-types src/inline_snapshot tests`
- Build docs strictly: `hatch run docs:build`
- Serve docs: `hatch run docs:serve`
- Run pre-commit on all files: `pre-commit run -a`

If dependencies are missing, prefer `uv run --group dev ...` before adding new tooling.

## Testing Guidance

New tests should usually use `inline_snapshot.testing.Example` from `src/inline_snapshot/testing/_example.py`. This is also called out in `CONTRIBUTING.md` as the preferred style.

- Use `Example(...).run_inline(...)` for fast in-process tests of snapshot behavior and source rewrites.
- Use `Example(...).run_pytest(...)` when behavior depends on the real pytest plugin, assertion rewriting, subprocess execution, terminal output, or pytest reports.
- Use `snapshot_arg()` in tests when expected values themselves should be snapshot-managed.
- Many tests compare changed files, report text, stderr, outcomes, or raised exceptions; keep these assertions explicit.
- CPython-only rewriting tests are skipped on PyPy unless marked with `@pytest.mark.no_rewriting`.
- The suite has a hard 100% coverage requirement in CI. Add tests with code changes, and use `# pragma: no cover` only for genuinely untestable paths.

Snapshot-changing tests may rewrite files. Review diffs carefully after running tests with update flags such as `--inline-snapshot=create,fix,update,trim` or shortcuts from `[tool.inline-snapshot]`.

## Formatting and Style

- Black and isort are used; isort is configured with `profile = "black"` and `force_single_line = true`.
- Pre-commit also runs pyupgrade, autoflake, blacken-docs, YAML formatting, actionlint, typos, and pyproject validation.
- Keep imports in the existing single-import-per-line style.
- The public API is exported from `src/inline_snapshot/__init__.py`; update `__all__` when adding public symbols.
- `py.typed` is present, so public typing quality matters.

## Pytest Plugin and Configuration Notes

- The pytest plugin is registered through `[project.entry-points.pytest11]` as `inline_snapshot = "inline_snapshot.pytest_plugin"`.
- The main CLI option is `--inline-snapshot=` with flags including `disable`, `short-report`, `report`, `review`, `create`, `update`, `trim`, `fix`, and insider-only `fix-assert`.
- Project configuration is read from `[tool.inline-snapshot]` in `pyproject.toml`.
- Custom shortcut options may be generated from inline-snapshot config.
- xdist is detected and affects snapshot session behavior.
- Assertion rewriting is registered for `inline_snapshot.extra` and `inline_snapshot.testing._example`.

## Documentation

Docs are built with MkDocs Material. The nav and plugins are configured in `mkdocs.yml`.

- Source docs live under `docs/`.
- The docs build watches `CONTRIBUTING.md`, `CHANGELOG.md`, `README.md`, `src/inline_snapshot`, and `changelog.d`.
- Use `hatch run docs:build` before touching docs-heavy changes when feasible.

## Changelog and Release Notes

For user-visible changes, create a scriv fragment:

```bash
uvx scriv create --add
```

Fill in only the relevant headings in the generated `changelog.d/*.md` file. Do not edit `CHANGELOG.md` manually; it is assembled by `scriv collect`.

## Current Workspace Caution

At the time this file was created, `src/inline_snapshot/_adapter_context.py` already had uncommitted changes. Treat unrelated local modifications as user work and do not revert them.
