# inline-snapshot

[![Docs](https://img.shields.io/badge/docs-mkdocs-green)](https://15r10nk.github.io/inline-snapshot/)
[![pypi version](https://img.shields.io/pypi/v/inline-snapshot.svg)](https://pypi.org/project/inline-snapshot/)
![PyPI - Downloads](https://img.shields.io/pypi/dw/inline-snapshot)
[![GitHub Sponsors](https://img.shields.io/github/sponsors/15r10nk)](https://github.com/sponsors/15r10nk)

> *create and update inline snapshots in your code.*

## Installation

You can install "inline-snapshot" via [pip](https://pypi.org/project/pip/):

``` bash
pip install inline-snapshot
```

## Usage

You can use `snapshot()` instead of the value which you want to compare with.

```python
from inline_snapshot import snapshot


def test_something():
    assert 1548 * 18489 == snapshot()
```

You can now run the tests and record the correct values.

```
$ pytest --inline-snapshot=create
```

```python
from inline_snapshot import snapshot


def test_something():
    assert 1548 * 18489 == snapshot(28620972)
```

## Features

- manage snapshots with `pytest --inline-snapshot=(create,update,fix,trim)`.
- uses `repr()` to convert the value to python code.
- values are stored in the source code and not in separate files.
- `snapshot()` supports the following operations:
  - `x == snapshot()`
  - `x <= snapshot()`
  - `x >= snapshot()`
  - `x in snapshot()`
  - `snapshot()[key]`
- code is formatted with black if the file was already formatted with black.

More information can be found in the [documentation](https://15r10nk.github.io/inline-snapshot/).

## Contributing

Contributions are very welcome.
Tests can be run with [nox](https://nox.thea.codes/en/stable/).
Please use [pre-commit](https://pre-commit.com/) for your commits.

## License

Distributed under the terms of the [MIT](http://opensource.org/licenses/MIT) license, "inline-snapshot" is free and open source software.

## Issues

If you encounter any problems, please [file an issue](https://github.com/15r10nk/inline-snapshot/issues) along with a detailed description.
