# Performance benchmarks

Run from the repository root with Python 3.12.

## Run locally

```bash
# Register this machine, then validate the working tree without saving timings.
uv run --group benchmark -p 3.12 asv machine --yes
uv run --group benchmark -p 3.12 asv run --python=same --quick --show-stderr --dry-run

# Compare committed revisions using the current benchmark suite.
uv run --group benchmark -p 3.12 asv continuous HEAD~1 HEAD

# Record history and view the dashboard.
uv run --group benchmark -p 3.12 asv run 'main~10..main' --record-samples
uv run --group benchmark -p 3.12 asv publish
uv run --group benchmark -p 3.12 asv preview
```

Use `--bench bench_pytest` to select pytest sessions. Historical runs ignore
uncommitted library changes and require revisions compatible with the suite.
Keep the machine and environment consistent; back up `.asv/results/`, which is
ignored by Git.

## What is measured

- **27 first-use comparison cases:** nine shapes (scalar, text, small/large
  schemas, spans, matchers, dataclasses, errors, Pydantic models), each with
  active snapshots, disabled snapshots, and plain equality. ASV `timeraw`
  starts a fresh Python process for every sample, with no snapshot warmup.
  Each timing is **ten assertions**, executed once at distinct snapshot call
  sites in one file. It includes the first source read, AST processing, inline
  expected-value construction, and final correctness checks. Later assertions
  in the batch can naturally reuse the file's source cache. Process startup,
  imports, fixture loading, actual-value construction, and cleanup are outside
  timing. This is a cold start of snapshot processing, not of the OS file cache.
- **Five pytest sessions:** active, disabled, create, fix, and update. Each runs
  ten tests in a fresh process, including startup, reporting, and source edits.
- **Retained snapshot state:** the recursive size of the session snapshot registry
  after evaluating 100 distinct active scalar call sites. Each call frame has an
  unrelated 100 kB local payload, exposing accidental frame retention.

Workloads live in `_workloads.py`; `_fixtures.py` creates distinct call sites.
Keep expected values inline and increment `SUITE_VERSION` in `_fixtures.py`
when fixtures, helpers, or timing boundaries change.

## PR reports

CI measures the PR base and head on the same runner, then uploads raw results
and the comparison as `benchmark-results`. A separate workflow uses
[asv-perch](https://github.com/HaoZeke/asv-perch) to post the report, including for
fork PRs. Performance regressions are informational; benchmark errors fail CI.
Shared runners are noisy, so small timing differences need confirmation.

The commenting workflow becomes active once `benchmark-report.yml` is on the
default branch. See the [ASV guide](https://asv.readthedocs.io/en/stable/using.html)
for more commands.
