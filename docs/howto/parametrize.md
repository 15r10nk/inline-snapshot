
inline-snapshot can also be used with `pytest.mark.parametrize`.
All you have to do is to use `snapshot()` as a parameter for your test

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

and the missing value will be created for each run.

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

If you stack `@pytest.mark.parametrize`, use one snapshot object that stores all
combinations and index it by a stable key.

<!-- inline-snapshot: first_block outcome-passed=4 outcome-errors=4 -->
``` python
import pytest
from inline_snapshot import snapshot

# example generated output after --inline-snapshot=create
snapshot_results = snapshot()


@pytest.mark.parametrize("a", [1, 2])
@pytest.mark.parametrize("b", [10, 20])
def test_parametrize_stack(a, b):
    assert snapshot_results[f"{a}+{b}"] == a + b
```

After `--inline-snapshot=create`, it can look like this:

<!-- inline-snapshot: create first_block outcome-passed=4 -->
``` python
import pytest
from inline_snapshot import snapshot

# example generated output after --inline-snapshot=create
snapshot_results = snapshot({"1+10": 11, "2+10": 12, "1+20": 21, "2+20": 22})


@pytest.mark.parametrize("a", [1, 2])
@pytest.mark.parametrize("b", [10, 20])
def test_parametrize_stack(a, b):
    assert snapshot_results[f"{a}+{b}"] == a + b
```

For large values this currently works with `external()` + `outsource()`.

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

The values will then be stored in external files as json when you run pytest.

<!-- inline-snapshot: create first_block outcome-failed=4 -->
``` python
import pytest
from inline_snapshot import external, outsource, snapshot

external_snapshots = snapshot(
    {
        "[1]*10": external("uuid:e443df78-9558-467f-9ba9-1faf7a024204.json"),
        "[2]*10": external("uuid:23a7711a-8133-4876-b7eb-dcd9e87a1613.json"),
        "[1]*20": external("uuid:1846d424-c17c-4279-a3c6-612f48268673.json"),
        "[2]*20": external("uuid:fcbd04c3-4021-4ef7-8ca5-a5a19e4d6e3c.json"),
    }
)


@pytest.mark.parametrize("a", [1, 2])
@pytest.mark.parametrize("b", [10, 20])
def test_parametrize_stack_external(a, b):
    assert external_snapshots[f"[{a}]*{b}"] == outsource([a] * b)
```
