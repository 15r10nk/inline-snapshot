# Copilot Instructions

## Changelog entries

To create a new changelog entry, run:

```
uvx scriv create --add
```

This creates a new Markdown file in `changelog.d/` and stages it with git.
Then fill in the relevant section(s) in that file. The default template contains
headers for **Added**, **Changed**, **Fixed**, and **Removed** — delete the ones
that don't apply and write one or two sentences under the relevant header.

Example result in `changelog.d/<fragment>.md`:

```markdown
### Fixed

- Fixed snapshot comparison for external files when `_changes()` raises during report generation.
```

Do **not** edit `CHANGELOG.md` directly — that file is assembled from fragments via `scriv collect`.
