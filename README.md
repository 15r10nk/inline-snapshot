<!-- -8<- [start:Header] -->

<p align="center">
  <a href="https://15r10nk.github.io/inline-snapshot/latest/">
    <img src="docs/assets/logo.svg" width="500" alt="inline-snapshot">
  </a>
</p>

![ci](https://github.com/15r10nk/inline-snapshot/actions/workflows/ci.yml/badge.svg?branch=main)
[![Docs](https://img.shields.io/badge/docs-mkdocs-green)](https://15r10nk.github.io/inline-snapshot/latest/)
[![pypi version](https://img.shields.io/pypi/v/inline-snapshot.svg)](https://pypi.org/project/inline-snapshot/)
![Python Versions](https://img.shields.io/pypi/pyversions/inline-snapshot)
[![PyPI - Downloads](https://img.shields.io/pypi/dw/inline-snapshot)](https://pypacktrends.com/?packages=inline-snapshot&time_range=2years)
[![coverage](https://img.shields.io/badge/coverage-100%25-blue)](https://15r10nk.github.io/inline-snapshot/latest/contributing/#coverage)
[![GitHub Sponsors](https://img.shields.io/github/sponsors/15r10nk)](https://github.com/sponsors/15r10nk)
[![Discord](https://img.shields.io/discord/1435889192143159346)](https://discord.gg/bnSwDaaPTa)

<!-- -8<- [end:Header] -->

## Installation

You can install "inline-snapshot" via [pip](https://pypi.org/project/pip/):

``` bash
pip install inline-snapshot
```


## Key Features

- **support for normal assertions:** inline-snapshot can now also fix normal assertions which do not use `snapshot()` like:

    ``` python
    assert 1 + 1 == 3
    ```

    You can learn [here](https://15r10nk.github.io/inline-snapshot/latest/fix_assert/) more about this feature.


- **Intuitive Semantics:** `snapshot(x)` mirrors `x` for easy understanding.
- **Versatile Comparison Support:** Equipped with
    [`x == snapshot(...)`](https://15r10nk.github.io/inline-snapshot/latest/eq_snapshot/),
    [`x <= snapshot(...)`](https://15r10nk.github.io/inline-snapshot/latest/cmp_snapshot/),
    [`x in snapshot(...)`](https://15r10nk.github.io/inline-snapshot/latest/in_snapshot/), and
    [`snapshot(...)[key]`](https://15r10nk.github.io/inline-snapshot/latest/getitem_snapshot/).
- **No CLI arguments required:** you will get an nice report where you can review the snapshot changes when you run pytest (only for cpython > 3.11, you have to use --inline-snapshot=review on older versions).
- **Enhanced Control Flags:** Utilize various [flags](https://15r10nk.github.io/inline-snapshot/latest/pytest/) for precise control of which snapshots you want to change.
- **Preserved Formatting:** Retains formatting consistency with Black formatting or a custom [format-command](https://15r10nk.github.io/inline-snapshot/latest/configuration/#format-command).
- **External File Storage:** Store snapshots externally using `external("uuid:eb1167b3-67a9-4378-bc65-c1e582e2e662.json")` with support for custom file formats.
- **Seamless Pytest Integration:** Integrated seamlessly with pytest for effortless testing.
- **Integration into normal functions:** use [`snapshot_arg()`](https://15r10nk.github.io/inline-snapshot/latest/snapshot_arg) to convert the arguments of your function into snapshots.
- **Customizable:** code generation can be customized with [@customize](https://15r10nk.github.io/inline-snapshot/latest/plugin/#inline_snapshot.plugin.InlineSnapshotPluginSpec.customize)
- **Nested Snapshot Support:** snapshots can contain [other snapshots](https://15r10nk.github.io/inline-snapshot/latest/eq_snapshot/#inner-snapshots)
- **Fuzzy Matching:** Incorporate [dirty-equals](https://15r10nk.github.io/inline-snapshot/latest/eq_snapshot/#dirty-equals) for flexible comparisons within snapshots.
- **Dynamic Snapshot Content:** snapshots can contain [non-constant values](https://15r10nk.github.io/inline-snapshot/latest/eq_snapshot/#is)
- **Comprehensive Documentation:** Access detailed [documentation](https://15r10nk.github.io/inline-snapshot/latest) for complete guidance.


## Usage

You can use `snapshot()` instead of the value which you want to compare with.

<!-- inline-snapshot: first_block outcome-passed=1 outcome-errors=1 -->
``` python
from inline_snapshot import snapshot


def test_something():
    assert 1548 * 18489 == snapshot()
```

You can now run the tests and record the correct values.

```
$ pytest --inline-snapshot=review
```

<!-- inline-snapshot: create outcome-passed=1 outcome-errors=1 -->
``` python hl_lines="5"
from inline_snapshot import snapshot


def test_something():
    assert 1548 * 18489 == snapshot(28620972)
```

The following examples show how you can use inline-snapshot in your tests. Take a look at the
[documentation](https://15r10nk.github.io/inline-snapshot/latest) if you want to know more.

<!-- inline-snapshot: create fix trim first_block outcome-passed=1 outcome-errors=1 -->
``` python
from inline_snapshot import external, outsource, snapshot


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
        external("hash:8bf10bdf2c30*.txt")
    )

    assert "generates\nmultiline\nstrings" == snapshot(
        """\
generates
multiline
strings\
"""
    )
```


`snapshot_arg()` can also be used for function parameters:

<!-- inline-snapshot: create fix trim first_block outcome-passed=1 -->
``` python
import subprocess as sp
import sys
from inline_snapshot import snapshot_arg


def run_python(cmd, stdout="", stderr=""):
    result = sp.run([sys.executable, "-c", cmd], capture_output=True)
    assert result.stdout.decode() == snapshot_arg(stdout)
    assert result.stderr.decode() == snapshot_arg(stderr)


def test_cmd():
    run_python("print('hello world')", stdout="hello world\n")

    run_python(
        "1/0",
        stderr="""\
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ZeroDivisionError: division by zero
""",
    )
```

<!-- -8<- [start:Feedback] -->
## Feedback

inline-snapshot provides some advanced ways to work with snapshots.

I would like to know how these features are used to further improve this small library.
Let me know if you've found interesting use cases for this library via [twitter](https://twitter.com/15r10nk), [fosstodon](https://fosstodon.org/deck/@15r10nk) or in the github [discussions](https://github.com/15r10nk/inline-snapshot/discussions/new?category=show-and-tell).

<!--[[[cog
import requests,cog

url = "https://raw.githubusercontent.com/15r10nk/sponsors/refs/heads/main/sponsors_readme.md"
response = requests.get(url)
response.raise_for_status()  # Raise an exception for bad status codes
cog.out(response.text)
]]]-->
## Sponsors

I would like to thank my sponsors. Without them, I would not be able to invest so much time in my projects.

### Silver sponsor 🥈

<p align="center">
  <a href="https://pydantic.dev/logfire">
    <img src="https://pydantic.dev/assets/for-external/pydantic_logfire_logo_endorsed_lithium_rgb.svg" alt="logfire" width="300"/>
  </a>
</p>
<!--[[[end]]]-->

I have also started to offer [insider](https://15r10nk.github.io/inline-snapshot/latest/insiders/) features for inline-snapshot. I will only release features as insider features if they will not cause problems for you when used in an open source project.
I hope sponsoring will allow me to spend more time working on open source projects.
Thank you for using inline-snapshot, the future will be 🚀.

## Issues

If you encounter any problems, please [report an issue](https://github.com/15r10nk/inline-snapshot/issues) along with a detailed description.
<!-- -8<- [end:Feedback] -->

## License

Distributed under the terms of the [MIT](http://opensource.org/licenses/MIT) license, "inline-snapshot" is free and open source software.
