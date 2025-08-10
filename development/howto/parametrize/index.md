inline-snapshot can also be used with `pytest.mark.parametrize`. All you have to do is to use `snapshot()` as an parameter for your test

```
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

```
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
