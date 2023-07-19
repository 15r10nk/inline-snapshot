## Unreleased

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
