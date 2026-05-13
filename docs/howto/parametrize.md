
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

If you stack `@pytest.mark.parametrize`, use one snapshot object that stores all
combinations and index it by a stable key.

``` python
import pytest
from inline_snapshot import snapshot


expected_results = snapshot({"1+10": 11, "2+10": 12, "1+20": 21, "2+20": 22})


@pytest.mark.parametrize("a", [1, 2])
@pytest.mark.parametrize("b", [10, 20])
def test_parametrize_stack(a, b):
    assert expected_results[f"{a}+{b}"] == a + b
```

For large values this currently works with `external()` + `outsource()`:

``` python
import pytest
from inline_snapshot import external
from inline_snapshot import outsource
from inline_snapshot import snapshot


external_results = snapshot(
    {
        "[1]*10": external("uuid:15dd3796-a304-406a-a973-93208cddd8d1.json"),
        "[2]*10": external("uuid:d995eee2-62eb-4e6b-8051-7ead8e03a739.json"),
        "[1]*20": external("uuid:8aad6cca-8228-40a3-aa99-25dec17f01a0.json"),
        "[2]*20": external("uuid:61569e13-7804-4f0d-b69a-60c053c08690.json"),
    }
)


@pytest.mark.parametrize("a", [1, 2])
@pytest.mark.parametrize("b", [10, 20])
def test_parametrize_stack_external(a, b):
    assert external_results[f"[{a}]*{b}"] == outsource([a] * b)
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
