# Pydantic AI `--inline-snapshot=report` memory investigation

## Summary

Pydantic AI used approximately 2.1 GiB of peak memory with
`inline-snapshot==0.36.1` in report mode, compared with approximately 1.0 GiB
when inline-snapshot was disabled.

The `SnapshotData` prototype reduces peak memory to approximately 1.8 GiB when
used with the local optimized `executing` checkout. A pre-report RSS probe using
the released `executing` measured approximately 1.6 GiB after garbage
collection.

The prototype removes the original large direct frame-retention path. Most of
the remaining difference from disabled mode is source and AST state retained by
`executing`. A smaller number of `AdapterContext` objects remain because their
returned `SnapshotValue` facades are themselves still live.

## Benchmark results

The original peak-memory measurements were:

| Mode | Wall time | Peak memory |
|---|---:|---:|
| `0.36.1`, report, released `executing` | 2.3 min | 2.1 GiB |
| prototype, report, editable `executing` | 2.3 min | 1.8 GiB |
| `0.36.1`, disabled | 1.9 min | 1.0 GiB |

The editable `executing` branch lazily constructs its line-to-node and qualname
indexes. This explains its memory and runtime improvement, but it still retains
the base parsed source and AST cache.

## Pre-report object measurements

A temporary `pytest_sessionfinish(tryfirst=True)` hook measured state after a
full Pydantic AI test run and `gc.collect()`, immediately before
inline-snapshot generated its report.

| Measurement | Prototype report | Prototype disabled |
|---|---:|---:|
| Current RSS | 1,608 MiB | 1,000 MiB |
| GC-tracked objects | 5,079,094 | 2,126,212 |
| Snapshot registry entries | 4,359 | 0 |
| Selected operations | 4,269 | 0 |
| Unique `executing.Source` objects | 159 | 0 |
| AST nodes | 954,193 | 37,165 |
| Frames | 1,576 | 227 |
| `AdapterContext` objects | 577 | 0 |

All snapshot registry entries in report mode were `SnapshotData` objects.

One unrelated Pydantic AI terminal-width test failed consistently under Python
3.15 during these runs. Measurements were still collected at the intended
pre-report hook.

## Why source and AST state remains

`executing.Source.__source_cache_with_lines` caches a `Source` for every parsed
file. Each source contains its parsed AST. `executing` also adds parent links to
AST nodes, making a file's tree a connected object graph.

The snapshot state retains this graph through two mechanisms:

1. `SnapshotData.file` contains a `SourceFile`, which wraps an
   `executing.Source`.
2. `CustomCode._repr_str` can contain an AST node. That node's parent links
   connect it to the rest of the file tree.

The local `executing` changes avoid eagerly constructing some secondary indexes,
but do not change the lifetime of the source cache or base AST.

This source/AST state is therefore the dominant remaining difference between
report and disabled mode.

## Attribution of the 577 retained `AdapterContext` objects

All 577 contexts were accounted for.

### 532 contexts: retained snapshot facades

532 contexts were owned directly by live `SnapshotValue` objects. These
facades were retained by module-level pytest parameter definitions and similar
case objects. For example:

```python
@pytest.mark.parametrize(
    "value,expected",
    [
        (0, snapshot("0")),
        (0.0, snapshot("0.000")),
    ],
)
def test_render(value, expected):
    assert render(value) == expected
```

Pytest retains parameter tuples, dictionaries and case objects for the entire
session. The ownership probe found the facades retained by:

- 255 dictionaries;
- 245 tuples;
- persistent test case objects such as `Case`, `Cell`, `ModelCase`, and
  `ResumedContentCase`.

As a focused confirmation, `tests/evals/test_render_numbers.py` produced 66
contexts. That module contains 66 snapshots in parameter definitions, and the
probe found exactly 66 live facades owned by 66 parameter tuples and 66 pytest
dictionaries.

This behavior follows the current lifetime rule: a facade's `AdapterContext`
remains alive while the object returned by `snapshot()` remains alive.

### 45 contexts: nested snapshot facades

The other 45 contexts were reachable from the global snapshot registry through
the following path:

```text
SnapshotData._new_value
→ CustomDict
→ CustomUnmanaged
→ dirty_equals.IsJson.expected_value
→ SnapshotValue._context
```

These are nested matcher expressions such as:

```python
IsJson(snapshot(...))
```

The outer snapshot retains the unmanaged `IsJson` matcher, and that matcher
retains the nested snapshot facade. The 45 contexts retain 29 distinct frames
because multiple nested snapshots originate from the same frame.

This is registry-mediated retention, but it also follows the facade lifetime
rule: the nested snapshot result remains part of a retained value.

## Synthetic frame-retention benchmark

The inline-snapshot ASV suite now includes a retained-state benchmark with 100
distinct active scalar call sites. Every call frame contains an unrelated
100 kB local payload.

| Revision | Recursively retained state |
|---|---:|
| `0.36.1` / `main` | 10,395,316 bytes |
| `SnapshotData` prototype | 351,244 bytes |

This is an approximately 97% reduction and confirms that ordinary completed
call frames are no longer retained through the session registry.

## Conclusions

- The `SnapshotData` architecture fixes the main direct frame-retention issue.
- The 577 remaining contexts are not an unexplained cache: 532 belong to
  intentionally live facades and 45 belong to nested facades inside retained
  matcher values.
- Most remaining memory is associated with the 159 parsed source files and
  roughly 954,000 live AST nodes.
- Reducing the remaining memory will require addressing source/AST lifetime or
  replacing retained AST references with compact source-location or rendered
  representations. It is separate from the original completed-frame retention
  fix.
