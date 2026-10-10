# Performance benchmarks

This ASV suite measures common `snapshot()` workloads without installing the
downstream projects. Run commands from the repository root with Python 3.12.

## Quick check

```bash
uv run --group benchmark -p 3.12 asv machine --yes
uv run --group benchmark -p 3.12 asv check --python=same
uv run --group benchmark -p 3.12 asv run --python=same --quick --show-stderr --dry-run
```

The first command records machine information in `~/.asv-machine.json`.
The quick run validates all cases against the working tree; its timings are
not suitable for comparisons and are not saved. The benchmark dependency group
is separate from the normal development/test dependencies.

## Record and compare commits

```bash
# Build and benchmark the committed HEAD in ASV's isolated environment.
uv run --group benchmark -p 3.12 asv run 'HEAD^!' --record-samples

# Measure both revisions on the same machine and report changes.
uv run --group benchmark -p 3.12 asv continuous HEAD~1 HEAD

# Backfill recent commits, then measure new commits on main.
uv run --group benchmark -p 3.12 asv run 'main~10..main' --record-samples
uv run --group benchmark -p 3.12 asv run NEW --record-samples

# Generate and view a local history dashboard.
uv run --group benchmark -p 3.12 asv publish
uv run --group benchmark -p 3.12 asv preview
```

The dashboard includes `main` and the current checkout (`HEAD`), so measurements
on a feature branch are visible before merging. For ongoing main-only tracking,
run `NEW` from main or remove `HEAD` from the configured branches.

Historical runs install the selected revision, ignoring uncommitted library
edits. ASV uses the current benchmark suite to measure those revisions. The
suite accesses private snapshot state to isolate initialization, so backfills
are intended for recent compatible revisions; older revisions may need a
compatibility adapter. Keep that adapter out of the measured operation.

Use `--bench 'bench_snapshot.Comparison.*schema'` to select schema cases, or
`--bench bench_pytest` for full pytest sessions. Use `--cpu-affinity` to select
an appropriate core on your benchmark machine. Do not run benchmarks alongside
tests, builds, or other heavy work.

## What is measured

`Comparison.time_comparison` has eight shapes, each measured in four modes.
`ModelComparison` adds a separate Pydantic workload: **36 comparison cases**.
Each result is elapsed time for **ten assertions**, not one assertion.

| Shape | Contents and motivation |
| --- | --- |
| scalar | An integer; lower-bound snapshot overhead |
| text | 100 lines of deterministic text, like captured logs/output |
| schema | Three OpenAPI-style paths with nested dictionaries/lists |
| schema_large | 200 paths; conversion and source-size scaling |
| spans | 20 nested span dictionaries with literal fields |
| matchers | The same spans, with `IsStr()` and `IsInt()` expectations |
| events | 50 nested dataclass events, like streamed model responses |
| errors | Five validation-error dictionaries containing tuple locations |
| models | 50 nested Pydantic model instances; optional-adapter workload |

The modes are:

- `first`: ten distinct call sites with an empty snapshot registry, but warm
  source/AST caches. Includes argument construction and initial comparison.
- `repeated`: ten visits to one already initialized call site, representing
  loops and parameterized tests.
- `disabled`: ten assertions with snapshot processing disabled.
- `plain`: ten equivalent assertions without `snapshot()`.

Actual values are built outside timing; inline expected arguments are evaluated
inside timing, as they are in real tests. Fixtures are written to real source
files and loaded before measurement. Source lookup and successful comparisons
are validated in setup. The module is reused between samples to avoid growing
source caches with new filenames. A fresh snapshot context is created outside
each timed batch. ASV uses `number=1` so initialization is never averaged
together with repeated visits inside a sample.

`PytestSession.time_session` adds **five process-level cases**: active matching,
disabled matching, create, fix, and update. Each starts a new Python process and
runs ten tests. These timings include interpreter/plugin startup, assertion
rewriting, source parsing, reporting, and (where applicable) file rewriting.
They do not imply cold operating-system disk caches. Creation/fixing uses small
schema snapshots; update converts equal float literals to integer literals.

Source files are restored by setup before every measurement. Teardown checks
pytest outcomes, that rewrites happened only when expected, and that the
rewritten snapshots match. The active/disabled state is checked inside pytest,
with explicit flags so CI's automatic disabling cannot invalidate measurements.
Only the inline-snapshot plugin is loaded; user pytest settings are ignored.

## Corpus and reproducibility

Workloads are defined in `_workloads.py` as readable Python source templates.
Large data shapes use deterministic builders whose values are rendered as
inline literals. Create, fix, and update each have their own template.
`_fixtures.py` expands the template's `test_snapshot()` into ten distinct
functions and loads the resulting source file. Keep expected values inside
`snapshot(...)`: moving them to a variable changes the work being measured.

`corpus.json` records the local checkout revisions, counts, size distributions,
and example locations used to choose these synthetic fixtures. It counts
static call sites, not how often tests execute them. It includes pydantic-ai's
`_inline_snapshot` wrapper, which selects the real library when snapshot flags
are enabled. No downstream implementation or full test body is copied.

Regenerate the survey intentionally, without fetching or running downstream code:

```bash
python scripts/survey_snapshots.py test-repos > benchmarks/corpus.json
```

Changes to that survey do not automatically change benchmark inputs. Keep
fixtures fixed for longitudinal comparisons. Increment `SUITE_VERSION` in
`_fixtures.py` whenever fixtures, helpers, or timing boundaries change; ASV
cannot reliably detect changes to imported helpers by hashing the benchmark
method alone. Version changes deliberately break comparison with old results.

`asv.conf.json` fixes the Python minor version and benchmark dependency versions.
Keep the Python patch version, operating system, hardware, and dependency
environment consistent too. Treat environment upgrades as new comparison
series. Pydantic is installed for the whole configured environment but measured
in its own family; filtering that family does not remove its plugin.

## Retaining history

ASV stores machine metadata, commit results, statistics, and requested raw
samples in `.asv/results/`. This directory is ignored by Git. **Back it up or
archive it in a separate results repository after recorded runs**; it is the
durable history from which `.asv/html/` can be regenerated. `.asv/env/` is a
disposable environment cache. Keep the benchmark definitions/configuration
alongside the archived results so their meaning remains recoverable.

For ongoing tracking, run `asv run NEW --record-samples` on the same dedicated
machine after updating main, archive results, and regenerate the dashboard.
The included CI workflow only checks benchmark correctness. Shared hosted
runners are too variable to establish small regressions, and no performance
threshold gates PRs. Establish repeated baseline measurements before choosing
regression thresholds or scheduling a dedicated runner.

See the [ASV user guide](https://asv.readthedocs.io/en/stable/using.html) for
historical runs and publishing, and
[benchmark definitions](https://asv.readthedocs.io/en/stable/writing_benchmarks.html)
for setup and parameterization.
