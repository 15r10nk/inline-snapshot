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
