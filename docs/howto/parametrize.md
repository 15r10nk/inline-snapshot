
inline-snapshot can also be used with `pytest.mark.parametrize`.

## One parametrize

You can use `snapshot()` as a parameter for your test.

<!-- inline-snapshot: first_block outcome-passed=2 outcome-errors=2 -->
``` python
import pytest
from inline_snapshot import snapshot


@pytest.mark.parametrize(
    "a,b,result",
    [
        (1, 2, snapshot()),
        (3, 4, snapshot()),
    ],
)
def test_param(a, b, result):
    assert a + b == result
```

The missing values will be created on the next run.

<!-- inline-snapshot: create outcome-passed=2 outcome-errors=2 -->
``` python hl_lines="8 9"
import pytest
from inline_snapshot import snapshot


@pytest.mark.parametrize(
    "a,b,result",
    [
        (1, 2, snapshot(3)),
        (3, 4, snapshot(7)),
    ],
)
def test_param(a, b, result):
    assert a + b == result
```

## Multiple parametrize

Stacking `@pytest.mark.parametrize` creates a cross-product of all combinations, so `snapshot()` can no longer be used as an argument.
Instead, use a single snapshot object that stores all combinations indexed by a stable key.

<!-- inline-snapshot: first_block outcome-passed=9 outcome-errors=9 -->
``` python
import pytest
from inline_snapshot import snapshot

snapshot_results = snapshot()


@pytest.mark.parametrize("a", [1, 2, 3])
@pytest.mark.parametrize("b", [10, 20, 30])
def test_parametrize_stack(a, b):
    assert snapshot_results[f"{a}+{b}"] == a + b
```

Once the snapshots are created, it looks like this:

<!-- inline-snapshot: create outcome-passed=9 outcome-errors=9 -->
``` python hl_lines="4 5 6 7 8 9 10 11 12 13 14 15 16"
import pytest
from inline_snapshot import snapshot

snapshot_results = snapshot(
    {
        "1+10": 11,
        "2+10": 12,
        "3+10": 13,
        "1+20": 21,
        "2+20": 22,
        "3+20": 23,
        "1+30": 31,
        "2+30": 32,
        "3+30": 33,
    }
)


@pytest.mark.parametrize("a", [1, 2, 3])
@pytest.mark.parametrize("b", [10, 20, 30])
def test_parametrize_stack(a, b):
    assert snapshot_results[f"{a}+{b}"] == a + b
```

## Store values externally

You can use `outsource()` when you want to store larger values.

<!-- inline-snapshot: first_block outcome-passed=4 outcome-errors=4 -->
``` python
import pytest
from inline_snapshot import external, outsource, snapshot

external_snapshots = snapshot()


@pytest.mark.parametrize("a", [1, 2])
@pytest.mark.parametrize("b", [10, 20])
def test_parametrize_stack_external(a, b):
    assert external_snapshots[f"[{a}]*{b}"] == outsource([a] * b)
```

The values will be stored in external JSON files when you run pytest.

<!-- inline-snapshot: create outcome-passed=4 outcome-errors=4 -->
``` python hl_lines="4 5 6 7 8 9 10 11"
import pytest
from inline_snapshot import external, outsource, snapshot

external_snapshots = snapshot(
    {
        "[1]*10": external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.json"),
        "[2]*10": external("uuid:f728b4fa-4248-4e3a-8a5d-2f346baa9455.json"),
        "[1]*20": external("uuid:eb1167b3-67a9-4378-bc65-c1e582e2e662.json"),
        "[2]*20": external("uuid:f7c1bd87-4da5-4709-9471-3d60c8a70639.json"),
    }
)


@pytest.mark.parametrize("a", [1, 2])
@pytest.mark.parametrize("b", [10, 20])
def test_parametrize_stack_external(a, b):
    assert external_snapshots[f"[{a}]*{b}"] == outsource([a] * b)
```
