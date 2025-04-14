
<a id='changelog-0.22.2'></a>
# 0.22.2 — 2025-04-14

## Fixed

- show correct diff when `pytest --inline-snapshot=report -vv` is used (#231)

<a id='changelog-0.22.1'></a>
# 0.22.1 — 2025-04-11

## Fixed

- The environment variable `INLINE_SNAPSHOT_DEFAULT_FLAGS` now takes precedence over all default flags defined in *pyproject.toml*.

- inline-snapshot can now be used in combination with `pytester.runpytest()`

<a id='changelog-0.22.0'></a>
# 0.22.0 — 2025-04-03

## Added

- You can now use the config option `skip-snapshot-updates-for-now` to skip the reporting of updates.
  But be aware that this option might not be there forever. Please create an issue if you think that the creation of snapshots can be improved.

<a id='changelog-0.21.3'></a>
# 0.21.3 — 2025-04-02

## Fixed

- Allowed inline-snapshot to work when pytest-xdist is disabled with `-n 0`.

<a id='changelog-0.21.2'></a>
# 0.21.2 — 2025-03-31

## Fixed

- `repr(Is(x))` returns the same value as `repr(x)` to provide nice pytest outputs (#217)

<a id='changelog-0.21.1'></a>
# 0.21.1 — 2025-03-29

## Changed

- trailing white spaces in multi-line strings are now terminated with an `\n\`.
    ``` python
    def test_something():
        assert "a   \nb\n" == snapshot(
            """\
    a   \n\
    b
    """
        )
    ```

<a id='changelog-0.21.0'></a>
# 0.21.0 — 2025-03-28

## Changed

- inline-snapshot uses now `--inline-snapshot=disable` during CI runs by default.
    This improves performance because `snapshot()` is then equal to:
    ``` python
    def snapshot(x):
        return x
    ```
    It also has benefits for the accuracy of your tests as it is less likely that inline snapshot will affect your tests in CI.

- The default flags have changed for cpython >= 3.11:
    * `--inline-snapshot=create,review` is used in an interactive terminal and
    * `--inline-snapshot=report` otherwise.

- The categories in the terminal output are now links to the documentation if it is supported by the terminal.

## Fixed

- Hide update section if the diff is empty because the change is reverted by the format-command.

<a id='changelog-0.20.10'></a>
# 0.20.10 — 2025-03-26

## Fixed

- Use of the correct snapshot category (update/fix) when deleting dataclass arguments.

<a id='changelog-0.20.9'></a>
# 0.20.9 — 2025-03-23

## Fixed

- `--inline-snapshot=create` preserves test failures now.

<a id='changelog-0.20.8'></a>
# 0.20.8 — 2025-03-20

## Fixed

- inline-snapshot now also works if you use `--no-summary` (which pycharm does if you run your tests from the IDE).

<a id='changelog-0.20.7'></a>
# 0.20.7 — 2025-03-14

## Changed

- Tests with failed snapshot comparisons now always result in a pytest `Error`, even if snapshots have been fixed or created.

<a id='changelog-0.20.6'></a>
# 0.20.6 — 2025-03-13

## Fixed

- Do not skip snapshots in conditional marked xfail tests.
  ``` python
  @pytest.mark.xfail(False, reason="...")
  def test_a():
      assert 5 == snapshot(3)  # <- this will be fixed


  @pytest.mark.xfail(True, reason="...")
  def test_b():
      assert 5 == snapshot(3)  # <- this not
  ```

<a id='changelog-0.20.5'></a>
# 0.20.5 — 2025-03-04

## Fixed

- correct normalization of "python3.9" to "python" in tests

<a id='changelog-0.20.4'></a>
# 0.20.4 — 2025-03-03

## Fixed

- Prevent a crash if a value cannot be copied and a UsageError is raised.

<a id='changelog-0.20.3'></a>
# 0.20.3 — 2025-02-28

## Fixed

- Use the black API directly to format python code.
  This solves issues with the upcoming click 8.2.0 (#202) and problems in multithreading (https://github.com/15r10nk/inline-snapshot/pull/193#issuecomment-2660393512).

<a id='changelog-0.20.2'></a>
# 0.20.2 — 2025-02-13

## Fixed

- snapshots inside tests which are marked as xfail are now ignored (#184)

- Fixed a crash caused by the following code:

   ``` python
   snapshot(tuple())
   # or
   snapshot(dict())
   ```

<a id='changelog-0.20.1'></a>
# 0.20.1 — 2025-02-04

## Fixed

- Fixed a windows bug with the readline module (#189)

<a id='changelog-0.20.0'></a>
# 0.20.0 — 2025-02-01

## Changed

- pytest assert rewriting works now together with inline-snapshot if you use `cpython>=3.11`

- `...` is now a special value to *create* snapshot values.
   The value change in `assert [5,4] == snapshot([5,...])` is now a *create* (previously it was a *fix*)

## Fixed

- fixed some issues with dataclass arguments

- fixed an issue where --inline-snapshot=review discarded the user input and never formatted
  the code if you used cpython 3.13.

<a id='changelog-0.19.3'></a>
# 0.19.3 — 2025-01-15

## Fixed

- raise no assertion for positional arguments inside constructor methods.

<a id='changelog-0.19.2'></a>
# 0.19.2 — 2025-01-15

## Fixed

- fixed a crash when you changed the snapshot to use a custom constructor method for dataclass/pydantic models.

    example:
    ``` python
    from inline_snapshot import snapshot
    from pydantic import BaseModel


    class A(BaseModel):
        a: int

        @classmethod
        def from_str(cls, s):
            return cls(a=int(s))


    def test_something():
        assert A(a=2) == snapshot(A.from_str("1"))
    ```

<a id='changelog-0.19.1'></a>
# 0.19.1 — 2025-01-12

## Added

- added the optional `inline-snapshot[dirty-equals]` dependency to depend on the dirty-equals version which works in combination with inline-snapshot.

## Fixed

- snapshots with pydantic models can now be compared multiple times

    ``` python
    class A(BaseModel):
        a: int


    def test_something():
        for _ in [1, 2]:
            assert A(a=1) == snapshot(A(a=1))
    ```

<a id='changelog-0.19.0'></a>
# 0.19.0 — 2025-01-10

## Added

- You can now specify which tool you want to use to format your code by setting a `format-command` in your [configuration](https://15r10nk.github.io/inline-snapshot/latest/configuration/#format-command).

## Changed

- **BREAKING-CHANGE** you have to install `inline-snapshot[black]` now if you want to format your code like in the previous versions. This option is not required if you use a `format-command`.

## Fixed

- Load default config values even if `[tool.inline-snapshot]` is missing.
  This makes the documented default shortcuts `--review` and `--fix` work.

<a id='changelog-0.18.2'></a>
# 0.18.2 — 2025-01-02

## Changed

- added `[dependency-groups]` to *pyproject.toml* and use uv and pytest to run tests in CI.

## Fixed

- use '.model_fields' on pydantic model class and not instance. This fixes a deprecation warning in the upcoming pydantic v2.11 (#169)

<a id='changelog-0.18.1'></a>
# 0.18.1 — 2024-12-22

## Fixed

- uv is now only used during test time if you run the inline-snapshot tests with `pytest --use-uv`
  This solves a problem if you want to package inline-snapshot in distributions (#165)

<a id='changelog-0.18.0'></a>
# 0.18.0 — 2024-12-21

## Added

- Support for a new `storage-dir` configuration option, to tell inline-snapshot where to store data files such as external snapshots.

## Fixed

- pydantic v1 is supported again. pydantic v1 & v2 create now the same snapshots. You can use `.dict()` to get the same snapshots like in inline-snapshot-0.15.0 for pydantic v1.

    ``` python
    class M(BaseModel):
        name: str


    def test_pydantic():
        m = M(name="Tom")
        assert m == snapshot(M(name="Tom"))
        assert m.dict() == snapshot({"name": "Tom"})
    ```

- Find `pyproject.toml` file in parent directories, not just next to the Pytest configuration file.

<a id='changelog-0.17.1'></a>
# 0.17.1 — 2024-12-17

## Fixed

- Code generation for sets is now deterministic.
  ``` python
  def test():
      assert {1j, 2j, 1, 2, 3} == snapshot({1, 1j, 2, 2j, 3})
  ```

<a id='changelog-0.17.0'></a>
# 0.17.0 — 2024-12-14

## Added

- [attrs](https://www.attrs.org/en/stable/index.html) can now contain unmanaged values

    ``` python
    import datetime as dt
    import uuid
    import attrs
    from dirty_equals import IsDatetime
    from inline_snapshot import Is, snapshot


    @attrs.define
    class Attrs:
        ts: dt.datetime
        id: uuid.UUID


    def test():
        id = uuid.uuid4()

        assert Attrs(dt.datetime.now(), id) == snapshot(
            Attrs(ts=IsDatetime(), id=Is(id))
        )
    ```

<a id='changelog-0.16.0'></a>
# 0.16.0 — 2024-12-12

## Added

- [`inline_snapshot.extra.warns`](https://15r10nk.github.io/inline-snapshot/latest/extra/#inline_snapshot.extra.warns) to captures warnings and compares them against expected warnings.
    ``` python
    def test_warns():
        with warns(snapshot([(8, "UserWarning: some problem")]), include_line=True):
            warn("some problem")
    ```

<a id='changelog-0.15.1'></a>
# 0.15.1 — 2024-12-10

## Fixed

- solved a bug caused by a variable inside a snapshot (#148)

<a id='changelog-0.15.0'></a>
# 0.15.0 — 2024-12-10

## Added

- snapshots [inside snapshots](https://15r10nk.github.io/inline-snapshot/latest/eq_snapshot/#inner-snapshots) are now supported.

    ``` python
    assert get_schema() == snapshot(
        [
            {
                "name": "var_1",
                "type": snapshot("int") if version < 2 else snapshot("string"),
            }
        ]
    )
    ```

- [runtime values](https://15r10nk.github.io/inline-snapshot/latest/eq_snapshot/#is) can now be part of snapshots.

    ``` python
    from inline_snapshot import snapshot, Is

    current_version = "1.5"
    assert request() == snapshot(
        {"data": "page data", "version": Is(current_version)}
    )
    ```

- [f-strings](https://15r10nk.github.io/inline-snapshot/latest/eq_snapshot/#f-strings) can now also be used within snapshots, but are currently not *fixed* by inline-snapshot.

## Changed

- *dirty-equals* expressions are now treated like *runtime values* or *snapshots* within snapshots and are not modified by inline-snapshot.

## Fixed

- inline-snapshot checks now if the given command line flags (`--inline-snapshot=...`) are valid

- `Example(...).run_pytest(raise=snapshot(...))` uses now the flags from the current run and not the flags from the Example.

<a id='changelog-0.14.2'></a>
# 0.14.2 — 2024-12-07

## Fixed

- do not crash when handling raw f-strings (`rf""`,`RF""`,...) (#143)

<a id='changelog-0.14.1'></a>
# 0.14.1 — 2024-12-04

## Fixed

- Don't crash for snapshots like `snapshot(f"")` (#139)
  It first appeared with pytest-8.3.4, but already existed before for cpython-3.11.
  f-strings in snapshots are currently not official supported, but they should not lead to crashes.

- skip formatting if black returns an error (#138)

<a id='changelog-0.14.0'></a>
# 0.14.0 — 2024-11-10

## Removed

- removed the `"Programming Language :: Python :: Implementation :: PyPy"` classifier which was incorrect, because inline-snapshot can not fix snapshots on pypy.
  inline-snapshot now enforces `--inline-snapshot=disable` when used with an implementation other than cpython, which allows it to be used in packages that want to support pypy.

## Added

- command line shortcuts can be defined to simplify your workflows. `--review` and `--fix` are defined by default. See the [documentation](https://15r10nk.github.io/inline-snapshot/latest/configuration/) for details.

## Changed

- `--inline-snapshot=create/fix/trim/update` will no longer show reports for other categories.
  You can use `--inline-snapshot=create,report` if you want to use the old behaviour.

<a id='changelog-0.13.4'></a>
# 0.13.4 — 2024-11-07

## Changed

- use tomli instead of toml (#130)

<a id='changelog-0.13.3'></a>
# 0.13.3 — 2024-09-24

## Fixed

- removed non-optional dirty-equals dependency (#118)

<a id='changelog-0.13.2'></a>
# 0.13.2 — 2024-09-24

## Changed

- star-expressions in list or dicts where never valid and cause a warning now.
    ```
        other=[2]
        assert [5,2]==snapshot([5,*other])
    ```

## Fixed

- A snapshot which contains an dirty-equals expression can now be compared multiple times.

    ``` python
    def test_something():
        greeting = "hello"
        for name in ["alex", "bob"]:
            assert (name, greeting) == snapshot((IsString(), "hello"))
    ```
## v0.13.1 (2024-09-18)

### Fix

- Use tomllib instead of PyPI toml on Python 3.11 and later

## v0.13.0 (2024-09-10)

### Feat

- added extra.prints
- 3.13 support
- strings with one line-break at the end become no multiline strings

## v0.12.1 (2024-08-05)

### Fix

- add license to project metadata and some other fixes in pyproject.toml (#104)

## v0.12.0 (2024-07-22)

### Feat

- implement extra.raises
- added inline_snapshot.testing.Example which can be used to test 3rd-party extensions

## v0.11.0 (2024-07-07)

### Feat

- check if the result of copy.deepcopy() is equal to the copied value
- support for `enum.Enum`, `enum.Flag`, `type` and omitting of default values (#73)

## v0.10.2 (2024-05-28)

### Fix

- changed how --inline-snapshot=disable works in combination with xdist (#90)
- fix typo, rename 'theme' with 'them'

## v0.10.1 (2024-05-26)

### Fix

- trigger no update for trailing comma changes

## v0.10.0 (2024-05-21)

### BREAKING CHANGE

- removed support for python 3.7
- removed `--inline-snapshot-disable` option and replaced it with `--inline-snapshot=disable`

### Feat

- new flags: *disable*, *short-report*, *report* and *review*
- added config option and environment variable to specify default flags
- show diff of changed snapshots in pytest report
- interactive *review* mode

## v0.9.0 (2024-05-07)

### Feat

- check if inline-snapshot is used in combination with xdist and notify the user that this is not possible

### Fix

- change the quoting of strings does not trigger an update

## v0.8.2 (2024-04-24)

### Fix

- removed restriction that the snapshot functions has to be called snapshot (#72)
- report error in tear down for sub-snapshots with missing values (#70)
- element access in sub-snapshots does not create new values

## v0.8.1 (2024-04-22)

### Fix

- make typing less strict

## v0.8.0 (2024-04-09)

### Feat

- prevent dirty-equal values from triggering of updates
- fix lists by calculating the alignment of the changed values
- insert dict items
- delete dict items
- preserve not changed dict-values and list-elements

### Fix

- update with UndecidedValue
- handle dicts with multiple insertions and deletions
- handle lists with multiple insertions and deletions
- fixed typing and coverage

### Refactor

- removed old _needs_* logic
- removed get_result
- use _get_changes api for DictValue
- use _get_changes api for CollectionValue
- use _get_changes api for MinMaxValue
- use _get_changes
- moved some functions

## v0.7.0 (2024-02-27)

### Feat

- removed old --update-snapshots option

## v0.6.1 (2024-01-28)

### Fix

- use utf-8 encoding to read and write source files

## v0.6.0 (2023-12-10)

### Feat

- store snapshot values in external files

## v0.5.2 (2023-11-13)

### Fix

- remove upper bound from dependency in pyproject.toml

## v0.5.1 (2023-10-20)

### Fix

- show better error messages

## v0.5.0 (2023-10-15)

### Feat

- support 3.12

### Fix

- do not change empty snapshot if it is not used

## v0.4.0 (2023-09-29)

### Feat

- escaped linebreak at the start/end of multiline strings

### Fix

- added py.typed

## v0.3.2 (2023-07-31)

### Fix

- handle update flag in sub-snapshots correctly
- fixed some edge cases where sub-snapshots had problems with some flags
- string literal concatenation should trigger no update

## v0.3.1 (2023-07-14)

### Fix

- added `__all__` to inline_snapshot
- flags fix/trim/create/update are changing the matching snapshots

## v0.3.0 (2023-07-12)

### BREAKING CHANGE

- values have to be copyable with `copy.deepcopy`

### Fix

- snapshot the current value of mutable objects
  ``` python
  l = [1]
  assert l == snapshot([1])  # old behaviour: snapshot([1, 2])
  l.append(2)
  assert l == snapshot([1, 2])
  ```

## v0.2.1 (2023-07-09)

### Fix

- black configuration files are respected

## v0.2.0 (2023-06-20)

### Feat

- `value <= snapshot()` to ensure that something gets smaller/larger over time (number of iterations of an algorithm you want to optimize for example),
- `value in snapshot()` to check if your value is in a known set of values,
- `snapshot()[key]` to generate new sub-snapshots on demand.

- convert strings with newlines to triple quoted strings
  ``` python
  assert "a\nb\n" == snapshot(
      """a
  b
  """
  )
  ```
- preserve black formatting


## v0.1.2 (2022-12-11)

### Fix

- updated executing

## v0.1.1 (2022-12-08)

### Fix

- fixed typo in pytest plugin name

## v0.1.0 (2022-07-25)

### Feat

- first inline-snapshot version
