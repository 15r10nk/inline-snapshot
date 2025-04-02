# Contributing
Contributions are welcome.
Please create an issue before writing a pull request so we can discuss what needs to be changed.

# Testing
The code can be tested with [hatch](https://hatch.pypa.io/latest/tutorials/testing/overview/)

* `hatch test` can be used to test all supported python versions and to check for coverage.
* `hatch test -py 3.10 -- --sw` runs pytest for python 3.10 with the `--sw` argument.

The preferred way to test inline-snapshot is by using [`inline-snapshot.texting.Example`](https://15r10nk.github.io/inline-snapshot/latest/testing/).
You will see some other fixtures which are used inside the tests, but these are old ways to write the tests and I try to use the new `Example` class to write new tests.


# Coverage
This project has a hard coverage requirement of 100% (which is checked in CI).
You can also check the coverage locally with `hatch test -acp`.
The goal here is to find different edge cases which might have bugs.

However, it is possible to exclude some code from the coverage.

Code can be marked with `pragma: no cover`, if it can not be tested for some reason.
This makes it easy to spot uncovered code in the source.

Impossible conditions can be handled with `assert False`.
``` python
if some_condition:
    ...
if some_other_condition:
    ...
else:
    assert False, "unreachable because ..."
```
This serves also as an additional check during runtime.

# Commits
Please use [pre-commit](https://pre-commit.com/) for your commits.
