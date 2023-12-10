<!-- -8<- [start:Header] -->

<p align="center">
  <a href="https://15r10nk.github.io/inline-snapshot/">
    <img src="https://raw.githubusercontent.com/15r10nk/inline-snapshot/main/docs/assets/logo.svg" width="500" alt="inline-snapshot">
  </a>
</p>

![ci](https://github.com/15r10nk/inline-snapshot/actions/workflows/ci.yml/badge.svg?branch=main)
[![Docs](https://img.shields.io/badge/docs-mkdocs-green)](https://15r10nk.github.io/inline-snapshot/)
[![pypi version](https://img.shields.io/pypi/v/inline-snapshot.svg)](https://pypi.org/project/inline-snapshot/)
![Python Versions](https://img.shields.io/pypi/pyversions/inline-snapshot)
![PyPI - Downloads](https://img.shields.io/pypi/dw/inline-snapshot)
[![coverage](https://img.shields.io/badge/coverage-100%25-blue)](https://15r10nk.github.io/inline-snapshot/contributing/#coverage)
[![GitHub Sponsors](https://img.shields.io/github/sponsors/15r10nk)](https://github.com/sponsors/15r10nk)

<!-- -8<- [end:Header] -->

## Installation

You can install "inline-snapshot" via [pip](https://pypi.org/project/pip/):

``` bash
pip install inline-snapshot
```

## Key Features

- **Intuitive Semantics:** `snapshot(x)` mirrors `x` for easy understanding.
- **Versatile Comparison Support:** Equipped with `x == snapshot(...)`, `x <= snapshot(...)`, `x in snapshot(...)`, and `snapshot(...)[key]`.
- **Enhanced Control Flags:** Utilize various [flags](https://15r10nk.github.io/inline-snapshot/pytest/) for precise control of which snapshots you want to change.
- **Preserved Black Formatting:** Retains formatting consistency with Black formatting.
- **External File Storage:** Store snapshots externally using `outsource(data)`.
- **Seamless Pytest Integration:** Integrated seamlessly with pytest for effortless testing.
- **Comprehensive Documentation:** Access detailed [documentation](https://15r10nk.github.io/inline-snapshot/) for complete guidance.


## Usage

You can use `snapshot()` instead of the value which you want to compare with.

<!-- inline-snapshot: outcome-errors=1 outcome-passed=1 -->
```python
from inline_snapshot import snapshot


def test_something():
    assert 1548 * 18489 == snapshot()
```

You can now run the tests and record the correct values.

```
$ pytest --inline-snapshot=create
```

<!-- inline-snapshot: create -->
```python
from inline_snapshot import snapshot


def test_something():
    assert 1548 * 18489 == snapshot(28620972)
```

inline-snapshot provides more advanced features like:

<!-- inline-snapshot: fix create trim this -->
```python
from inline_snapshot import snapshot, outsource, external


def test_something():
    for number in range(5):
        # testing for numeric limits
        assert number <= snapshot(4)
        assert number >= snapshot(0)

    for c in "hello world":
        # test if something is part of a set
        assert c in snapshot(["h", "e", "l", "o", " ", "w", "r", "d"])

    s = snapshot(
        {
            0: {"square": 0, "pow_of_two": False},
            1: {"square": 1, "pow_of_two": True},
            2: {"square": 4, "pow_of_two": True},
            3: {"square": 9, "pow_of_two": False},
            4: {"square": 16, "pow_of_two": True},
        }
    )

    for number in range(5):
        # create sub-snapshots at runtime
        assert s[number]["square"] == number**2
        assert s[number]["pow_of_two"] == (
            (number & (number - 1) == 0) and number != 0
        )

    assert outsource("large string\n" * 1000) == snapshot(
        external("8bf10bdf2c30*.txt")
    )
```

<!-- -8<- [start:Feedback] -->
## Feedback

inline-snapshot provides some advanced ways to work with snapshots.

I would like to know how these features are used to further improve this small library.
Let me know if you've found interesting use cases for this library via [twitter](https://twitter.com/15r10nk) or in the github [discussions](https://github.com/15r10nk/inline-snapshot/discussions/new?category=show-and-tell).

## Issues

If you encounter any problems, please [report an issue](https://github.com/15r10nk/inline-snapshot/issues) along with a detailed description.
<!-- -8<- [end:Feedback] -->

## License

Distributed under the terms of the [MIT](http://opensource.org/licenses/MIT) license, "inline-snapshot" is free and open source software.
