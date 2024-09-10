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
- handle dicts with mulitple insertions and deletions
- handle lists with mulitple insertions and deletions
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

- remove upper bound from dependencies in pyproject.toml

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
