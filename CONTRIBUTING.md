# Contributing
Contributions are welcome.
Please create an issue before writing a pull request so we can discuss what needs to be changed.

# Testing
The code can be tested with [hatch](https://hatch.pypa.io/latest/)

* `hatch run cov:test` can be used to test all supported python versions and to check for coverage.
* `hatch run +py=3.10 all:test -- --sw` runs pytest for python 3.10 with the `--sw` argument.


# Coverage
This project has a hard coverage requirement of 100%.
The goal here is to find different edge cases which might have bugs.

However, it is possible to exclude some code from the coverage.

Code can be marked with `pragma: no cover`, if it can not be tested for some reason.
This makes it easy to spot uncovered code in the source.

Impossible conditions can be handled with `assert False`.
``` python
if some_condition:
    ...
if some_other_codition:
    ...
else:
    assert False, "unreachable because ..."
```
This serves also as an additional check during runtime.


# Commits
Please use [pre-commit](https://pre-commit.com/) for your commits.
