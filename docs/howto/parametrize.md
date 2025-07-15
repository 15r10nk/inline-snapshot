
inline-snapshot can also be used with `pytest.mark.parametrize`.
All you have to do is to use `snapshot()` as an parameter for your test

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
