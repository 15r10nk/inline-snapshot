
## pytest assert rewriting is disabled

inline-snapshot must disable pytest assert-rewriting if you use *report/review/create/fix/trim/update* flags and *cpython<3.11*.

## xdist is not supported

You can not use inline-snapshot in combination with `pytest-xdist`. The use of `-n=...` implies `--inline-snapshot=disable`.

## works only with cpython

inline-snapshot works currently only with cpython. `--inline-snapshot=disable` is enforced for every other implementation.
