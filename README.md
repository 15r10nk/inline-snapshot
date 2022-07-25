inline-snapshot
======================

create and update inline snapshots in your code.

Features
--------

* records current values during [pytest](https://github.com/pytest-dev/pytest) run `--update-snapshots=new`.
* values are stored in the source code and not in separate files.
* values can be updated with `--update-snapshots=failing`.


Installation
------------

You can install "inline-snapshot" via `pip`_ from `PyPI`_::

    $ pip install inline-snapshot


Usage
-----

``` python
def something():
    return 1548 * 18489


def test_something():
    assert something() == snapshot()
```

The tests will pass because there is no value to compare with.
You can now run the tests and record the correct values.

``` bash
pytest --update-snapshots=new
```

``` python
def something():
    return 1548 * 18489


def test_something():
    assert something() == snapshot(28620972)  # snapshot gets recorded
```

Your tests will break if you change your code later.
You get normal pytest failure messages, because `snapshot(x)` just returns `x`.

``` python
def something():
    return (1548 * 18489) // 18


def test_something():
    assert something() == snapshot(28620972)  # this will fail because code changed
```

Maybe that is correct and you should fix your code, or
your code is correct and you want to update your test results.

``` shell
pytest --update-snapshots=failing
```

Please verify the new results. `git diff` will give you a good overview over all changed results.

``` python
def something():
    return (1548 * 18489) // 18


def test_something():
    assert something() == snapshot(1590054)
```

The code is generated without any formatting.
Use the formatter of your choice to make it look nice, or maybe use [darker](https://pypi.org/project/darker/) if you only want to format your changes.


More than just numbers
----------------------

Value requirements:
* the values should be comparable with `==`
* `repr(value)` should return valid python code


You can use almost any python datatype and also complex values like `datatime.date`

``` python
from inline_snapshot import snapshot
import datetime


def something():
    return {
        "name": "hello",
        "one number": 5,
        "numbers": list(range(10)),
        "sets": {1, 2, 15},
        "datetime": datetime.date(1, 2, 22),
        "complex stuff": 5j + 3,
        "bytes": b"fglecg\n\x22",
    }


def test_something():
    assert something() == snapshot(
        {
            "name": "hello",
            "one number": 5,
            "numbers": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            "sets": {1, 2, 15},
            "datetime": datetime.date(1, 2, 22),
            "complex stuff": (3 + 5j),
            "bytes": b'fglecg\n"',
        }
    )
```


`snapshot()` can also be used in loops

``` python
from inline_snapshot import snapshot


def test_loop():
    for name in ["Mia", "Ava", "Leo"]:
        assert len(name) == snapshot(3)
```



Contributing
------------
Contributions are very welcome. Tests can be run with `tox`_.
Please use pre-commit for your commits

License
-------

Distributed under the terms of the [MIT](http://opensource.org/licenses/MIT) license, "inline-snapshot" is free and open source software


Issues
------

If you encounter any problems, please `file an issue`_ along with a detailed description.

.. _`Cookiecutter`: https://github.com/audreyr/cookiecutter
.. _`MIT`: http://opensource.org/licenses/MIT
.. _`file an issue`: https://github.com/15r10nk/pytest-inline-snapshot/issues
.. _`pytest`: https://github.com/pytest-dev/pytest
.. _`tox`: https://tox.readthedocs.io/en/latest/
.. _`pip`: https://pypi.org/project/pip/
.. _`PyPI`: https://pypi.org/project
